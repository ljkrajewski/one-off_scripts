import os
import shutil
import hashlib
from pathlib import Path
import stat
import time
import argparse
import fnmatch
import logging
import sys
from datetime import datetime

def setup_logging(log_file, verbose):
    """Set up logging to file or stdout with specified verbosity."""
    logger = logging.getLogger('backup_script')
    logger.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Set up handler based on log_file
    if log_file:
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler(sys.stdout)
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger, verbose

def parse_ignore_file(ignore_file_path, logger, verbose):
    """Parse .backup_ignore file and return a list of patterns."""
    patterns = []
    if os.path.exists(ignore_file_path):
        if verbose:
            logger.info(f"Reading ignore patterns from {ignore_file_path}")
        with open(ignore_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Normalize pattern: remove leading/trailing slashes, handle dir/
                    pattern = line.rstrip('/').lstrip('/')
                    patterns.append(pattern)
    return patterns

def is_ignored(rel_path, ignore_patterns):
    """Check if a relative path matches any ignore patterns."""
    # Check if the path or any of its parent directories match an ignore pattern
    path_parts = rel_path.split(os.sep)
    for i in range(len(path_parts) + 1):
        sub_path = os.sep.join(path_parts[:i]) or rel_path
        for pattern in ignore_patterns:
            # Handle directory patterns (e.g., dir/ or dir)
            if pattern.endswith('/'):
                pattern = pattern.rstrip('/')
                if fnmatch.fnmatch(sub_path, pattern) or fnmatch.fnmatch(sub_path + '/', pattern + '/*'):
                    return True
            # Handle file patterns and wildcards
            elif fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(sub_path, pattern):
                return True
    return False

def calculate_md5(file_path):
    """Calculate MD5 checksum of a file."""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def get_dest_files(dest_dir, ignore_patterns, logger, verbose):
    """Get list of all files in destination directory, excluding ignored files."""
    dest_files = []
    for root, _, files in os.walk(dest_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, dest_dir)
            if not is_ignored(rel_path, ignore_patterns):
                dest_files.append(rel_path)
    if verbose:
        logger.info(f"Found {len(dest_files)} files in destination directory")
    return dest_files

def get_src_files_with_md5(src_dir, backup_type, timestamp_file, ignore_patterns, logger, verbose):
    """Get dictionary of source files with their MD5 checksums, filtered by backup type and ignore patterns."""
    src_files = {}
    files_skipped = 0
    timestamp_mtime = None
    if backup_type == "incr" and timestamp_file:
        if not os.path.exists(timestamp_file):
            raise FileNotFoundError(f"Timestamp file {timestamp_file} does not exist")
        timestamp_mtime = os.path.getmtime(timestamp_file)
        if verbose:
            logger.info(f"Using timestamp file {timestamp_file} with mtime {timestamp_mtime}")
    
    for root, _, files in os.walk(src_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, src_dir)
            # Skip ignored files
            if ignore_patterns and is_ignored(rel_path, ignore_patterns):
                if verbose:
                    logger.info(f"Skipping ignored file: {rel_path}")
                files_skipped += 1
                continue
            # Check file modification time for incremental backup
            if backup_type == "incr" and timestamp_mtime:
                file_mtime = os.path.getmtime(file_path)
                if file_mtime <= timestamp_mtime:
                    if verbose:
                        logger.info(f"Skipping file {rel_path} (mtime {file_mtime} <= timestamp mtime {timestamp_mtime})")
                    files_skipped += 1
                    continue
            src_files[rel_path] = calculate_md5(file_path)
    if verbose:
        logger.info(f"Found {len(src_files)} files in source directory for backup, skipped {files_skipped} files")
    return src_files, files_skipped

def copy_file_with_metadata(src_path, dest_path, logger, verbose):
    """Copy file preserving metadata and verify with MD5."""
    # Create parent directory if needed
    dest_dir = os.path.dirname(dest_path)
    if dest_dir and not os.path.exists(dest_dir):
        try:
            os.makedirs(dest_dir)
            if verbose:
                logger.info(f"Created directory: {dest_dir}")
        except OSError as e:
            logger.error(f"Failed to create directory {dest_dir}: {e}")
            raise
    
    # Copy file preserving metadata
    try:
        shutil.copy2(src_path, dest_path)
        if verbose:
            logger.info(f"Successfully copied {src_path} to {dest_path}")
    except OSError as e:
        logger.error(f"Failed to copy {src_path} to {dest_path}: {e}")
        raise
    
    # Verify MD5
    src_md5 = calculate_md5(src_path)
    dest_md5 = calculate_md5(dest_path)
    if src_md5 != dest_md5:
        logger.error(f"Verification failed for {dest_path}: MD5 mismatch")
        raise RuntimeError(f"Verification failed for {dest_path}")
    
    # Copy ownership
    src_stat = os.stat(src_path)
    try:
        shutil.chown(dest_path, src_stat.st_uid, src_stat.st_gid)
        if verbose:
            logger.info(f"Set ownership for {dest_path} (uid: {src_stat.st_uid}, gid: {src_stat.st_gid})")
    except PermissionError as e:
        logger.warning(f"Could not set ownership for {dest_path}: {e}")
    
    return 1  # Return 1 to indicate one file was copied

def backup_directory(src_dir, dest_dir, backup_type, timestamp_file, logger, verbose):
    """Perform backup from src_dir to dest_dir based on backup type."""
    start_time = time.time()
    logger.info(f"Starting {backup_type} backup from {src_dir} to {dest_dir}")
    
    # Initialize counters
    files_copied = 0
    files_skipped = 0
    files_deleted = 0
    
    # Ensure directories exist
    src_dir = Path(src_dir).resolve()
    dest_dir = Path(dest_dir).resolve()
    
    if not src_dir.exists():
        logger.error(f"Source directory {src_dir} does not exist")
        raise FileNotFoundError(f"Source directory {src_dir} does not exist")
    if not dest_dir.exists():
        logger.error("DEST directory doesn't exist")
        raise FileNotFoundError("DEST directory doesn't exist")
    
    # Load ignore patterns from .backup_ignore
    ignore_file = src_dir / '.backup_ignore'
    ignore_patterns = parse_ignore_file(ignore_file, logger, verbose)
    
    # Get files lists
    dest_files = get_dest_files(dest_dir, ignore_patterns, logger, verbose) if backup_type == "full" else []
    src_files, skipped_from_filters = get_src_files_with_md5(src_dir, backup_type, timestamp_file, ignore_patterns, logger, verbose)
    files_skipped += skipped_from_filters
    
    # Process each source file
    for rel_path, src_md5 in src_files.items():
        src_path = src_dir / rel_path
        dest_path = dest_dir / rel_path
        
        # Check if file exists in destination
        copy_needed = True
        if rel_path in dest_files:
            dest_files.remove(rel_path)
            # Compare MD5 checksums
            if os.path.exists(dest_path):
                dest_md5 = calculate_md5(dest_path)
                if src_md5 == dest_md5:
                    copy_needed = False
                    files_skipped += 1
                    if verbose:
                        logger.info(f"Skipping {rel_path}: MD5 matches")
        
        # Copy file if needed
        if copy_needed:
            try:
                files_copied += copy_file_with_metadata(src_path, dest_path, logger, verbose)
            except Exception as e:
                logger.error(f"Error copying {rel_path}: {e}")
                raise
    
    # Delete remaining files in destination (only for full backup)
    if backup_type == "full":
        for rel_path in dest_files:
            dest_path = dest_dir / rel_path
            try:
                os.remove(dest_path)
                files_deleted += 1
                logger.info(f"Deleted {rel_path}")
                # Clean up empty directories
                parent = dest_path.parent
                while parent != dest_dir:
                    try:
                        parent.rmdir()
                        if verbose:
                            logger.info(f"Removed empty directory: {parent}")
                        parent = parent.parent
                    except OSError:
                        break
            except OSError as e:
                logger.warning(f"Could not delete {rel_path}: {e}")
    
    # Update timestamp file timestamp
    if timestamp_file:
        try:
            with open(timestamp_file, "a"):
                os.utime(timestamp_file, None)  # Update to current time
            if verbose:
                logger.info(f"Updated timestamp file {timestamp_file}")
        except OSError as e:
            logger.warning(f"Could not update timestamp file {timestamp_file}: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Backup completed successfully: {files_copied} files copied, {files_skipped} files skipped, {files_deleted} files deleted in {duration:.2f} seconds")

def main():
    parser = argparse.ArgumentParser(description="Backup directory with MD5 verification")
    parser.add_argument("src", help="Source directory")
    parser.add_argument("dest", help="Destination directory")
    parser.add_argument("--type", choices=["full", "incr"], default="full",
                        help="Backup type: full or incr")
    parser.add_argument("--timestamp", help="Path to timestamp file for incr backup")
    parser.add_argument("--log", "-l", help="Path to log file (default: stdout)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Include all actions in log (successful/failed copies, directory creations, etc.)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.type == "incr" and not args.timestamp:
        parser.error("Incremental backup requires --timestamp argument")
    
    # Set up logging
    logger, verbose = setup_logging(args.log, args.verbose)
    
    try:
        backup_directory(args.src, args.dest, args.type, args.timestamp, logger, verbose)
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
