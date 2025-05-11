# Louisbot4
discord message statistics bot

# how it works
louisbot sits in the background and logs a timestamp pointer to the first message of a new batch, then once the batch has been 
filled (once at least n culmative messages have been sent in all servers it is deployed in) the batch is processed, 
louisbot fetches the message history after the pointer, increments each users data and then writes to disk.

all of its data is stored in json format as files seperated by weeks under `<database_dir>/data/` in `<year>y-<month>m-<week>w.json` format
the maximum granularity thus is 1 week.
