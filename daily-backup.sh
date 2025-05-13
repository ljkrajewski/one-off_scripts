#!/usr/bin/bash
# Usage: ./daily_backups.sh SRC_DIR DEST_DIR

SRC=$1
DEST=$2
LOGFILE=/var/log/backup/$(basename $SRC)-`date +"%Y%m%d%H%M"`.log

echo SRC = $SRC
echo DEST = $DEST
echo LOG = $LOGFILE

echo -- backup begun:  `date` > $LOGFILE
echo SRC = $SRC >> $LOGFILE
echo DEST = $DEST >> $LOGFILE
echo LOG = $LOGFILE >> $LOGFILE

# safe checks.
if [ ! -d $1 ]; then
  echo Source directory $1 does not exist. Aborting backup. >> $LOGFILE
  exit 1
fi
if [ ! -d $2 ]; then
  echo Destination directory $2 does not exist. Aborting backup. >> $LOGFILE
  exit 1
fi

rsync -avrR --stats --delete --checksum --checksum-choice=md5 --log-file=$LOGFILE $SRC $DEST

gzip -9 $LOGFILE
