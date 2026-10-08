#!/usr/bin/env bash

# Scan all script.txt files under the current directory
# and report whether each file contains a '$' symbol.

rm -rf  scan_dollar_in_scriptxt.log
find . -type f -name "script.txt" | sort | while IFS= read -r file; do
    echo scanning "$file"
    if grep -q '\$' "$file"; then
        #echo "$file : contains \$" 
	echo "$file : contains \$" > scan_dollar_in_scriptxt.log
		newfilename="${file%.txt}_bk.tx"
		#echo "$newfilename"
		#echo mv "$file" "$newfilename"
		#mv "$file" "$newfilename"
		#echo ''
#    else
#        echo "$file : no \$"

    fi
done

if [ ! -s scan_dollar_in_scriptxt.log ]; then
	    echo scan_dollar_in_scriptxt.log is empty. No script.txt scanned contains "'\$'"
    else
	    cat scan_dollar_in_scriptxt.log
fi
