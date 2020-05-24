# automate-weekly-track-roundup
a python program that finds the most recent "theneedledrop" weekly track roundup video. scrapes vid description, collects youtube links to songs mentioned in vid, and automatically adds them to youtube playlists sorted by best, meh, and worst tracks of the week. also, scrapes "artist - title" text descriptions and searches for these songs on spotify, creates best/meh/worst spotify playlists, and adds these songs to the created spotify playlists.

this program is triggered automatically weekly using the windows task scheduler. every week it will create new Spotify and Youtube playlists for the current week. it also cleans up your playlist section by deleting last week's previous playlists.
