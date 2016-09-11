#!/usr/bin/env python
"""
Script to export and update iTunes play counts.
"""
from Foundation import *
from ScriptingBridge import *
import os
import shutil
import sys
import time

def usage(error=None):
    if error:
        print >> sys.stderr, error, "\n"
    print >> sys.stderr, "playcounts.py [export|update] storage_dir"
    print >> sys.stderr, "\texport\tExport play counts and store at storage_dir"
    print >> sys.stderr, "\tupdate\tUpdate play counts from store at storage_dir"
    print >> sys.stderr, "\tstorage_dir\tDefaults to the Desktop."
    sys.exit(1)

def bail(error=None):
    if error:
        print >> sys.stderr, error, "\n"
    sys.exit(1)

def attrs():
    update_attrs = ["playedCount", "playedDate", "rating", "dateAdded"]
    update_attrs.extend(signature_attrs())
    return update_attrs

def signature_attrs():
    return ["name", "artist", "album", "time"]

def zerofilter_attrs():
    # Attributes to unset if they are 0.
    return ["rating", "playedCount"]

def track_to_dict(track):
    result = {}
    zerofilter = zerofilter_attrs()
    for attr in attrs():
        value = getattr(track, attr)()
        if not value:
            continue
        result[attr] = getattr(track, attr)()
        if attr in zerofilter and result[attr] == 0:
            del(result[attr])
    return result

def get_tracks():
    itunes = SBApplication.applicationWithBundleIdentifier_('com.apple.iTunes')
    library_playlist = itunes.sources()[0].libraryPlaylists()[0]
    tracks = library_playlist.tracks()
    print >> sys.stderr, "Found %d tracks." % tracks.count()
    return tracks

def track_to_filetrack(track):
    track_obj = track.get()
    if track_obj.__class__.__name__ == 'ITunesFileTrack':
        return track_obj
    else:
        return None

def tracks_to_data(tracks):
    data = []
    for track in tracks:
        track_obj = track_to_filetrack(track)
        if not track_obj:
            continue
        #location = track_obj.location()
        #if not location:
        #    print >> sys.stderr, "No location:", track_obj.name()
        #    continue
        #path = location.path()
        #if not os.path.exists(path):
        #    print >> sys.stderr, "Not found:", path
        data.append(track_to_dict(track_obj))
    return data

def backup_itunes_library():
    itunes_dir = os.path.expanduser("~/Music/iTunes/")
    backup_dir = os.path.join(itunes_dir, "Playcounts")
    if not os.path.exists(backup_dir):
        os.mkdir(backup_dir)
        if not os.path.exists(backup_dir):
            bail("Unable to create iTunes library backup directory at: " + backup_dir)
    itl_path = os.path.join(itunes_dir, "iTunes Library.itl")
    if not os.path.exists(itl_path):
        bail("Unable to find iTunes library at: " + itl_path)
    dest_path_fmt = "%s iTunes Library.itl"
    day = time.strftime("%Y-%m-%d")
    dest_path = os.path.join(backup_dir, dest_path_fmt % day)
    counter = 0
    while os.path.exists(dest_path):
        counter += 1
        dest_path_fmt = "%s-%02d iTunes Library.itl"
        dest_path = os.path.join(backup_dir, dest_path_fmt % (day, counter))
    shutil.copy2(itl_path, dest_path)
    if not os.path.exists(dest_path):
        bail("Unable to backup iTunes library to: " + dest_path)
    print >> sys.stderr, "iTunes library backed up to:", dest_path

class TracksByName(object):
    tracks = []
    by_name = {}
    def __init__(self, tracks):
        self.tracks = tracks
        for track in self.tracks:
            track_obj = track_to_filetrack(track)
            if not track_obj:
                continue
            name = track_obj.name()
            self.by_name.setdefault(name, [])
            self.by_name[name].append(track)
    def tracks_with_name(self, name):
        return self.by_name[name]

def track_matches_data(track, data):
    # Return true if the track matches the signature attributes in data.
    track_obj = track_to_filetrack(track)
    if not track_obj:
        return False
    attrs = signature_attrs()
    for attr in attrs:
        track_value = getattr(track, attr)()
        data_value = data.get(attr)
        if not data_value:
            print >> sys.stderr, "Missing signature value for", attr, "in track:", data.get('name')
            return False
        if track_value != data_value:
            print >> sys.stderr, track_value, "!=", data_value
            return False
    return True

def update_track_with_data(track, data):
    # Update the iTunes track with the given data.
    track_obj = track_to_filetrack(track)
    if not track_obj:
        return False
    actions = []
    # played count
    playedCount = data.get('playedCount', 0)
    if playedCount > 0:
        current_played_count = track_obj.playedCount()
        actions.append("Setting played count to %d from %d" % (playedCount + current_played_count, current_played_count))
    # played date
    playedDate = data.get('playedDate')
    if playedDate:
        current_played_date = track_obj.playedDate()
        if playedDate.compare_(current_played_date) == 1:
            # decending
            actions.append("Setting played date to: %s from %s" % (playedDate, current_played_date))
    # date added
    dateAdded = data.get('dateAdded')
    if dateAdded:
        current_date_added = track_obj.dateAdded()
        if dateAdded.compare_(current_date_added) == -1:
            # ascending
            actions.append("Setting date added to: %s from %s" % (dateAdded, current_date_added))
    # rating
    rating = data.get('rating')
    if rating:
        current_rating = track_obj.rating()
        if not current_rating:
            actions.append("Setting rating to: %d from %d" % (rating, current_rating))
    if len(actions):
        print >> sys.stderr, track_obj.name()
        for action in actions:
            print >> sys.stderr, "\t", action

def update_itunes_with_data(data, verbose=True):
    tracks = get_tracks()
    tracks_by_name = TracksByName(tracks)
    print >> sys.stderr, "%d Tracks" % data.count()
    for track_data in data:
        if not track_data.get('name'):
            print >> sys.stderr, "No name in track."
            continue
        matching_tracks = tracks_by_name.tracks_with_name(track_data['name'])
        for track in matching_tracks:
            if track_matches_data(track, track_data):
                update_track_with_data(track, track_data)

def main(argv):
    if len(argv) < 2:
        usage("Insufficient arguments.")
    command = argv[1]
    if len(argv) > 2:
        path = argv[2]
    else:
        path = "~/Desktop/"
    
    resolved_path = os.path.expanduser(path)
    if not os.path.exists(resolved_path):
        usage("Unable to find storage_dir: %s" % path)
    elif not os.path.isdir(resolved_path):
        usage("storage_dir must be a directory: %s" % path)
    elif not command in ["update", "export"]:
        usage("Unknown command: %s" % command)
    
    filepath = os.path.join(resolved_path, "playcounts.plist")
    
    if command == "export":
        tracks = get_tracks()
        data = tracks_to_data(tracks)
        #for track in data:
        #    print track
        nsa = NSArray(data)
        xml_plist_data, error = NSPropertyListSerialization.dataWithPropertyList_format_options_error_(nsa, NSPropertyListXMLFormat_v1_0, 0, None)
        if xml_plist_data:
            if not xml_plist_data.writeToFile_atomically_(filepath, True):
                bail("Unable to write output file to: " + filepath)
        else:
            print >> sys.stderr, "Error:", error
    elif command == "update":
        backup_itunes_library()
        data = NSArray.arrayWithContentsOfFile_(filepath)
        if not data:
            bail("Unable to read data from: " + filepath)
        update_itunes_with_data(data)
    
if __name__ == "__main__":
    main(sys.argv)
