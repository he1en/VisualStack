#!/bin/hash

if [ $# -ne 1 ]; then
    echo $0: usage: visualstack.sh filename.c
    exit 1
fi

clear

sqlite3 VisualStack.db < vscreate.sql;
python vsbase.py 7080 $1

#if which xdg-open > /dev/null
#then
#  xdg-open myth24.stanford.edu:8080/visualstack
#elif which gnome-open > /dev/null
#then
#  gnome-open myth24.stanford.edu:8080/visualstack
#fi
