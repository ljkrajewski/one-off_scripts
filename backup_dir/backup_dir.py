#!/usr/bin/env python3

import os
import shutil
import hashlib
import pathlib
import stat
import time
import argparse
import fnmatch
import logging
import sys
import datetime
import atexit
import errno
import hashlib as hash_lib

def setup_logging(log_file=None, verbose=False):
    """Configure logging with specified format and output."""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    level = logging.DEBUG if verbose else logging.INFO
    if log_file:
        logging.basicConfig(filename=log_file, level=level, format=log_format)
    else:
        logging.basicConfig(stream=sys.stdout, level=level, format=log_format)

def calculate_md5(file_path):
    """Calculate MD5 checksum of a file."""
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def read_ignore_patterns(ignore_file):
    """Read .backup_ignore file and return list of patterns."""
    patterns = []
    if os.path.exists(ignore_file):
        with open(ignore_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    return patterns

def is_ignored(path, patterns, root):
    """Check if a path matches any ignore patterns."""
    rel_path = os.path.relpath(path, root)
    for pattern in patterns:
        if pattern.endswith('/'):
            pattern = pattern.rstrip('/')
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(rel_path, f"{pattern}/*"):
                return True
        elif fnmatch.fnmatch(rel_path, pattern):
            return True
    return False

def create_lock_file(src_path):
    """Create a lock file for the source directory and return its path."""
    src_abs = os.path.abspath(src_path)
    src_hash = hash_lib.sha256(src_abs.encode()).hexdigest()
    lock_file = f"/tmp/backup_dir_{src_hash}.lock"
    
    try:
        # Check for existing lock file
        if os.path.exists(lock_file):
            with open(lock_file, 'r') as f:
                pid = f.read().strip()
                try:
                    pid = int(pid)
                    os.kill(pid, 0)  # Check if process is running
                    logging.error(f"Another instance is already running for source directory {src_path} (PID: {pid})")
                    sys.exit(1)
                except (ValueError, OSError):
                    logging.warning(f"Removing stale lock file {lock_file} (PID: {pid} not running)")
                    os.remove(lock_file)
        
        # Create new lock file
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        return lock_file
    except OSError as e:
        logging.error(f"Failed to create lock file {lock_file}: {e}")
        sys.exit(1)

def cleanup_lock_file(lock_file):
    """Remove the lock file."""
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except OSError as e:
        logging.warning(f"Failed to remove lock file {lock_file}: {e}")

def scan_source_directory(src, ignore_patterns, timestamp_mtime=None, verbose=False):
    """Scan source directory and return dictionary of files with metadata."""
    src_files = {}
    ignored_count = 0
    skipped_count = 0
    processed_count = 0
    
    for root, dirs, files in os.walk(src, followlinks=False):
        for name in files:
            src_path = os.path.join(root, name)
            rel_path = os.path.relpath(src_path, src)
            processed_count += 1
            
            if verbose and processed_count % 1000 == 0:
                logging.debug(f"Processed {processed_count} files for source directory dictionary")
            
            if is_ignored(src_path, ignore_patterns, src):
                if verbose:
                    logging.debug(f"Skipping ignored file: {rel_path}")
                ignored_count += 1
                continue
            
            stat_info = os.lstat(src_path)
            is_symlink = stat.S_ISLNK(stat_info.st_mode)
            
            # Skip files based on timestamp in incremental mode (except symlinks)
            if timestamp_mtime is not None and not is_symlink:
                if stat_info.st_mtime <= timestamp_mtime:
                    if verbose:
                        logging.debug(f"Skipping file due to timestamp: {rel_path}")
                    skipped_count += 1
                    continue
            
            src_files[rel_path] = {
                'path': src_path,
                'is_symlink': is_symlink,
                'mtime': stat_info.st_mtime,
                'mode': stat_info.st_mode,
                'uid': stat_info.st_uid,
                'gid': stat_info.st_gid,
                'md5': None,
                'link_target': None
            }
            
            if is_symlink:
                try:
                    src_files[rel_path]['link_target'] = os.readlink(src_path)
                except OSError as e:
                    logging.warning(f"Failed to read symlink {rel_path}: {e}")
            else:
                try:
                    src_files[rel_path]['md5'] = calculate_md5(src_path)
                except OSError as e:
                    logging.warning(f"Failed to calculate MD5 for {rel_path}: {e}")
    
    logging.info(f"Completed scanning source directory: {processed_count} files processed, "
                 f"{len(src_files)} included, ignored {ignored_count} files, "
                 f"skipped {skipped_count} files due to timestamp")
    return src_files, ignored_count, skipped_count

def scan_destination_directory(dest, src, ignore_patterns, verbose=False):
    """Scan destination directory and return list of files."""
    dest_files = []
    processed_count = 0
    
    for root, dirs, files in os.walk(dest, followlinks=False):
        for name in files:
            dest_path = os.path.join(root, name)
            rel_path = os.path.relpath(dest_path, dest)
            src_path = os.path.join(src, rel_path)
            processed_count += 1
            
            if verbose and processed_count % 1000 == 0:
                logging.debug(f"Processed {processed_count} files for destination directory list")
            
            if is_ignored(src_path, ignore_patterns, src):
                continue
            
            dest_files.append(rel_path)
    
    logging.info(f"Completed scanning destination directory: {processed_count} files processed, "
                 f"{len(dest_files)} included")
    return dest_files

def perform_backup(src_files, dest, backup_type, ignore_patterns, verbose=False):
    """Perform the backup operation."""
    files_copied = 0
    files_skipped = 0
    files_deleted = 0
    
    # Process source files
    for rel_path, info in src_files.items():
        dest_path = os.path.join(dest, rel_path)
        dest_dir = os.path.dirname(dest_path)
        
        # Ensure destination directory exists
        if not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir)
                if verbose:
                    logging.debug(f"Created directory: {dest_dir}")
            except OSError as e:
                logging.warning(f"Failed to create directory {dest_dir}: {e}")
                continue
        
        if info['is_symlink']:
            # Handle symbolic links
            if os.path.exists(dest_path) or os.path.islink(dest_path):
                try:
                    current_target = os.readlink(dest_path) if os.path.islink(dest_path) else None
                    if current_target == info['link_target']:
                        if verbose:
                            logging.debug(f"Skipping unchanged symlink: {rel_path}")
                        files_skipped += 1
                        continue
                    os.remove(dest_path)
                except OSError as e:
                    logging.warning(f"Failed to remove existing symlink {rel_path}: {e}")
            
            try:
                os.symlink(info['link_target'], dest_path)
                if verbose:
                    logging.debug(f"Copied symlink: {rel_path} -> {info['link_target']}")
                files_copied += 1
            except OSError as e:
                logging.warning(f"Failed to create symlink {rel_path}: {e}")
        else:
            # Handle regular files
            if os.path.exists(dest_path) and not os.path.islink(dest_path):
                try:
                    dest_md5 = calculate_md5(dest_path)
                    if dest_md5 == info['md5']:
                        if verbose:
                            logging.debug(f"Skipping unchanged file: {rel_path}")
                        files_skipped += 1
                        continue
                    os.remove(dest_path)
                except OSError as e:
                    logging.warning(f"Failed to process existing file {rel_path}: {e}")
            
            try:
                shutil.copy2(info['path'], dest_path)
                # Verify MD5 after copy
                dest_md5 = calculate_md5(dest_path)
                if dest_md5 != info['md5']:
                    logging.warning(f"MD5 verification failed for {rel_path}")
                    os.remove(dest_path)
                    continue
                
                # Attempt to preserve ownership
                try:
                    shutil.chown(dest_path, user=info['uid'], group=info['gid'])
                except OSError as e:
                    logging.warning(f"Could not set ownership for {rel_path}: {e}")
                
                if verbose:
                    logging.debug(f"Copied file: {rel_path}")
                files_copied += 1
            except OSError as e:
                logging.warning(f"Failed to copy file {rel_path}: {e}")
    
    # Delete extra files in destination (full mode only)
    if backup_type == 'full':
        dest_files = scan_destination_directory(dest, src, ignore_patterns, verbose)
        for rel_path in dest_files:
            if rel_path not in src_files:
                dest_path = os.path.join(dest, rel_path)
                try:
                    os.remove(dest_path)
                    if verbose:
                        logging.debug(f"Deleted extra file: {rel_path}")
                    files_deleted += 1
                except OSError as e:
                    logging.warning(f"Failed to delete extra file {rel_path}: {e}")
    
    return files_copied, files_skipped, files_deleted

def update_timestamp_file(timestamp_file, start_time, verbose=False):
    """Update timestamp file to backup start time."""
    if timestamp_file:
        try:
            os.utime(timestamp_file, (start_time, start_time))
            if verbose:
                logging.debug(f"Updated timestamp file {timestamp_file} to backup start time {start_time}")
        except OSError as e:
            logging.warning(f"Could not update timestamp file {timestamp_file}: {e}")

def main():
    """Main function to execute the backup script."""
    parser = argparse.ArgumentParser(description="Perform full or incremental backups with MD5 verification.")
    parser.add_argument('src', help="Source directory")
    parser.add_argument('dest', help="Destination directory")
    parser.add_argument('--type', choices=['full', 'incr'], default='full', help="Backup type (default: full)")
    parser.add_argument('--timestamp', help="Path to timestamp file (required for incr)")
    parser.add_argument('--log', '-l', help="Write logs to file")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable detailed logging")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not os.path.exists(args.src):
        logging.error(f"Source directory {args.src} does not exist")
        sys.exit(1)
    if not os.path.exists(args.dest):
        logging.error("DEST directory doesn't exist")
        sys.exit(1)
    if args.type == 'incr' and not args.timestamp:
        logging.error("Incremental backup requires --timestamp argument")
        sys.exit(1)
    
    # Setup logging
    setup_logging(args.log, args.verbose)
    
    # Create lock file
    lock_file = create_lock_file(args.src)
    atexit.register(cleanup_lock_file, lock_file)
    
    # Record start time
    start_time = time.time()
    logging.info(f"Starting {args.type} backup from {args.src} to {args.dest}")
    
    # Read ignore patterns
    ignore_file = os.path.join(args.src, '.backup_ignore')
    ignore_patterns = read_ignore_patterns(ignore_file)
    
    # Get timestamp mtime for incremental mode
    timestamp_mtime = None
    if args.type == 'incr':
        try:
            timestamp_mtime = os.stat(args.timestamp).st_mtime
        except OSError as e:
            logging.error(f"Failed to access timestamp file {args.timestamp}: {e}")
            sys.exit(1)
    
    # Scan directories
    src_files, ignored_count, skipped_count = scan_source_directory(
        args.src, ignore_patterns, timestamp_mtime, args.verbose
    )
    
    # Perform backup
    files_copied, files_skipped, files_deleted = perform_backup(
        src_files, args.dest, args.type, ignore_patterns, args.verbose
    )
    
    # Update timestamp file
    update_timestamp_file(args.timestamp, start_time, args.verbose)
    
    # Calculate duration and log summary
    duration = time.time() - start_time
    logging.info(f"Backup completed successfully: {files_copied} files copied, "
                 f"{files_skipped + skipped_count} files skipped, "
                 f"{files_deleted} files deleted in {duration:.2f} seconds")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
