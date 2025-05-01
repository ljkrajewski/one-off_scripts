# backup_dir(1) - User Commands

## NAME
**backup_dir** - Perform full or incremental backups with MD5 verification

## SYNOPSIS
**backup_dir** *src* *dest* [**--type** {full|incr}] [**--timestamp** *timestamp_file*] [**--log** *log_file* | **-l** *log_file*] [**--verbose** | **-v**]

## DESCRIPTION
**backup_dir** is a Python script that backs up files from a source directory (*src*) to a destination directory (*dest*). It supports full and incremental backups, preserves file metadata (permissions and ownership), verifies file integrity using MD5 checksums, and respects ignore patterns specified in a `.backup_ignore` file in the source directory. The destination directory (*dest*) must exist; if it does not, the script will exit with an error message ("DEST directory doesn't exist") and a non-zero status code. Logs are written to stdout by default or to a file specified by `--log`. With `--verbose`, logs include all actions (successful/failed file copies, directory creations, start/stop times, and execution duration); otherwise, successful copies and directory creations are omitted.

In **full** mode, the script copies all files from the source to the destination, overwriting files with different MD5 checksums and deleting files in the destination that are not in the source. In **incr** mode, it only copies files modified after the modification time of the specified *timestamp_file* and does not delete files from the destination.

## OPTIONS
- **src**  
  The source directory to back up (required).

- **dest**  
  The destination directory for the backup (required). Must exist prior to running the script.

- **--type** {full|incr}  
  Specify the backup type. **full** performs a complete backup, copying all files and deleting extra files in the destination. **incr** performs an incremental backup, copying only files modified after the timestamp file's modification time. Default: **full**.

- **--timestamp** *timestamp_file*  
  Path to a timestamp file used for incremental backups. Required for **incr** mode. The script only backs up files with a modification time newer than the timestamp file's modification time and updates the timestamp file's modification time after a successful backup.

- **--log** *log_file*, **-l** *log_file*  
  Path to a file where backup logs are written. If not specified, logs are written to stdout.

- **--verbose**, **-v**  
  Enable verbose logging, including all actions (successful/failed file copies, directory creations, start/stop times, and execution duration). Without this flag, successful copies and directory creations are omitted from the log.

## .backup_ignore FILE
The script reads a `.backup_ignore` file in the source directory to exclude files and directories from the backup. The file uses a syntax similar to `.gitignore`:

- Exact file paths (e.g., `file.txt`)
- Directory paths (e.g., `dir/` or `dir`)
- Wildcard patterns (e.g., `*.txt`, `logs/*`)
- Comments (lines starting with `#`)
- Blank lines (ignored)

Ignored files and directories are neither copied to the destination nor deleted from it.

## EXAMPLES
Perform a full backup with verbose logging to a file:
```
backup_dir /path/to/src /path/to/dest --type full --log backup.log --verbose
```

Perform an incremental backup with logs to stdout:
```
backup_dir /path/to/src /path/to/dest --type incr --timestamp /path/to/timestamp.txt
```

Example `.backup_ignore` file:
```
# Ignore log files
*.log
# Ignore temporary directory
temp/
# Ignore specific file
secret.txt
```

## EXIT STATUS
- **0**: Backup completed successfully.
- **1**: Backup failed due to an error (e.g., missing source directory, missing destination directory, invalid arguments).

## NOTES
- The script preserves file permissions and attempts to preserve ownership, but ownership preservation may fail without sufficient permissions.
- Hidden files (e.g., `.hidden`) are included in the backup unless excluded by `.backup_ignore`.
- The timestamp file is updated after a successful backup (both full and incr modes) if provided.
- In **incr** mode, files are selected based on their modification time (`mtime`), which reflects the last time the file's content was changed.

## BUGS
Report bugs to the script maintainer. Known limitations:
- Ownership preservation requires sufficient permissions.
- Complex `.gitignore` features (e.g., negated patterns like `!file.txt`) are not supported in `.backup_ignore`.

## AUTHOR
Written by an xAI assistant.

## SEE ALSO
- `cp(1)`
- `rsync(1)`
- `gitignore(5)`

*Generated on April 28, 2025*
