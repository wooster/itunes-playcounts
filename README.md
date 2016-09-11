# iTunes Playcounts Updater

This is a small script to export playcounts, ratings and other metadata from one iTunes installation, and import them on another.

The ideal use case is: you have a computer you're decommissioning, and want to add the played counts for all the songs on that computer (A) to the played counts of the songs on another computer (B). On A, you'd run:

`playcounts.py export`

Then copy the file at `~/Desktop/playcounts.plist` onto the Desktop of computer B. On B, run:

`playcounts.py update`

This will add the playcounts for each track on A to the corresponding tracks on B.

It will also set the ratings, the last played date to the latest date, and the date added to the earliest date.


## Limitations

* Very Alpha Quality.
* Only works on OS X.
* Use at your own risk.
