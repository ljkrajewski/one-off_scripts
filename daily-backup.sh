#!/usr/bin/bash
# Usage: ./daily_backups.sh SRC_DIR DEST_DIR

SRC=$1
SRCBASE=$(basename $SRC)
DEST=$2/$SRCBASE
TIME=$2/timestamp-$SRCBASE
LOGFILE=/var/log/backup/$SRCBASE-`date +"%Y%m%d%H%M"`.log
MD5FILE=/tmp/checksum-$SRCBASE.md5
THRESHOLD_DAYS=3
DOW=`date | awk '{print $1}'`
CURRENT_TIME=$(date +%s)
CREATION_TIME=$(stat -c %Y $TIME)
AGE_IN_DAYS=$(( (CURRENT_TIME - CREATION_TIME) / (60*60*24) ))

echo SRC = $SRC
echo DEST = $DEST
echo TIME = $TIME
echo LOG = $LOGFILE

if [[ $AGE_IN_DAYS -ge $THRESHOLD_DAYS ]]; then
  TYPE="full"
else
  TYPE="incr"
fi

echo -- $TYPE backup begun:  `date` > $LOGFILE
echo SRC = $SRC >> $LOGFILE
echo DEST = $DEST >> $LOGFILE
echo TIME = $TIME >> $LOGFILE
echo LOG = $LOGFILE >> $LOGFILE
echo MD5FILE = $MD5FILE >> $LOGFILE

# safe checks.
if [ ! -d $1 ]; then
  echo Source directory $1 does not exist. Aborting backup. >> $LOGFILE
  exit 1
fi
if [ ! -d $2 ]; then
  echo Destination directory $2 does not exist. Aborting backup. >> $LOGFILE
  exit 1
fi
if [ -f $TIME.new ]; then
  echo $TIME.new exists. Previous backup probably still running. Aborting backup. >> $LOGFILE
  exit 1
fi
if [ ! -f $TIME ]; then
  touch -d "@0" $TIME
fi

touch $TIME.new

# Make MD5 sum list
cd $SRC
if [[ "$TYPE" == "full" ]]; then
  find . -type f -print0 | xargs -0 md5sum > $MD5FILE
else
  find . -type f -newer $TIME -print0 | xargs -0 md5sum > $MD5FILE
fi

# Copy/verify src files to dest
while read -r line; do
  [ -z "$line" ] && continue                        # Skip empty lines
  expected_md5=$(echo "$line" | awk '{print $1}')   # Extract MD5 sum and filename
  filename=$(echo "$line" | awk '{print substr($0, 35)}')
  src_file="$SRC/$filename"
  dest_file="$DEST/$filename"
  if [ ! -f "$src_file" ]; then                     # Check if source file exixsts
    echo "Warning: Source file '$src_file' not found" >> $LOGFILE
    continue
  fi
  if [ ! -f "$dest_file" ]; then                    # If dest file doesn't exist,
    echo "Copying: $filename (destination file doesn't exist)" >> $LOGFILE
    cp -a "$src_file" "$dest_file"                  # ...copy it
    continue
  fi
  actual_md5=$(md5sum "$dest_file" | awk '{print $1}')  # Calc MD5 of dest file
  if [ "$expected_md5" != "$actual_md5" ]; then
    echo "Copying: $filename (MD5 mismatch)" >> $LOGFILE
    cp -a "$src_file" "$dest_file"
  else
    echo "Skipping: $filename (MD5 match)" >> $LOGFILE
  fi
done < "$MD5FILE"

# If full backup, delete files in dest that are not in src
find $DEST -type f | while read -r dest_file; do
  relative_path="${dest_file#$DEST/}"
  src_file="$SRC/$relative_path"
  if [ ! -f "$src_file" ]; then
    echo "Deleteing: $dest_file (no corresponding source file)" >> $LOGFILE
    rm -f "$dest_file"
  fi
done

echo -- $TYPE backup complete:  `date` >> $LOGFILE

# Cleanup  
rm $MD5FILE
rm $TIME
mv $TIME.new $TIME
gzip -9 $LOGFILE
