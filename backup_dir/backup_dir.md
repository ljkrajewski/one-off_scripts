backup_dir(1) - User Commands
NAME
backup_dir - Perform full or incremental backups with MD5 verification
SYNOPSIS
backup_dir src dest [--type {full|incr}] [--timestamp timestamp_file] [--log log_file | -l log_file] [--verbose | -v]
DESCRIPTION
The backup_dir script performs full or incremental backups from a source directory src to a destination directory dest on Unix-like systems. It supports MD5 checksum verification, metadata preservation (permissions, timestamps, ownership), symbolic link handling, and ignore patterns via a .backup_ignore file. The destination directory must exist. The script prevents concurrent runs for the same source directory using a lock file.
In full mode, all non-ignored files are copied, overwriting files with different MD5 checksums, and extra files in the destination are deleted. In incr mode, only files with modification times newer than the timestamp file's modification time are copied (except symbolic links, which are always included unless ignored), and no files are deleted. Hidden files are included unless ignored.
OPTIONS

srcSource directory to back up (required).

destDestination directory (required, must exist).

--type {full|incr}Backup type: full (default) or incr (incremental).

--timestamp timestamp_filePath to timestamp file. Required for incr mode; optional for full mode. Updated to backup start time after successful backup.

--log log_file | -l log_fileWrite logs to log_file instead of stdout.

--verbose | -vEnable detailed logging, including all file operations and progress.


.backup_ignore FILE
The .backup_ignore file in the source directory specifies files and directories to exclude, using .gitignore-like syntax:

Exact paths (e.g., file.txt)
Directories (e.g., dir/ or dir)
Wildcards (e.g., *.txt, logs/*)
Comments (lines starting with #)
Blank lines

Example:
*.log
temp/
# Ignore build outputs
build/*

Ignored files are not copied, deleted, or compared. Complex .gitignore features (e.g., negated patterns like !file.txt) are not supported.
EXAMPLES

Full backup with verbose logging:  
backup_dir /src /dest --type full --log backup.log --verbose


Incremental backup:  
backup_dir /src /dest --type incr --timestamp /path/to/timestamp.txt



EXIT STATUS

0: Successful backup.
1: Error (e.g., missing directories, invalid arguments, running instance for same source).

NOTES

Incremental mode uses file modification time (mtime) for selection, except for symbolic links, which are always included unless ignored.
Metadata preservation (e.g., ownership) may fail without sufficient permissions, logging a warning.
Hidden files (e.g., .file) are included unless ignored.
The timestamp file, if provided, is updated to the backup start time.
Instance locking uses a lock file in /tmp based on a SHA-256 hash of the source directory path, preventing concurrent runs for the same source.

BUGS

Ownership preservation may fail without root privileges, logging a warning.
The .backup_ignore file does not support complex .gitignore features like negated patterns.

AUTHOR
Written by an xAI assistant.
SEE ALSO

cp(1)
rsync(1)
gitignore(5)

