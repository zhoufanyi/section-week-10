import psycopg2
import psycopg2.extras
from psycopg2 import sql
import requests
from config import *
import sys
import json

DEBUG = True
CACHE_DICTION = {}
CACHE_FNAME = 'cache_file_name.json'
db_connection = None
db_cursor = None

# caching from Project 2 ------------------------------------------------------
def load_cache():
    global CACHE_DICTION
    try:
        cache_file = open(CACHE_FNAME, 'r')
        cache_contents = cache_file.read()
        CACHE_DICTION = json.loads(cache_contents)
        cache_file.close()
    except:
        CACHE_DICTION = {}

def save_cache():
    full_text = json.dumps(CACHE_DICTION)
    cache_file_ref = open(CACHE_FNAME,"w")
    cache_file_ref.write(full_text)
    cache_file_ref.close()

def params_unique_combination(baseurl, params_d, private_keys=["api_key"]):
    alphabetized_keys = sorted(params_d.keys())
    res = []
    for k in alphabetized_keys:
        if k not in private_keys:
            res.append("{}-{}".format(k, params_d[k]))
    return baseurl + "_".join(res)

def sample_get_cache_itunes_data(baseurl, params=None):
    if not params:
        params = {}

    unique_ident = params_unique_combination(baseurl, params)
    print(unique_ident)

    # if not in cache, get fresh data
    if unique_ident not in CACHE_DICTION:
        response = requests.get(baseurl, params=params)
        CACHE_DICTION[unique_ident] = json.loads(response.text)
        save_cache()
        if DEBUG:
            print('--> fresh copy')
    else:
        if DEBUG:
            print('--> from cache')

    return CACHE_DICTION[unique_ident]

class Song:
    def __init__(self, song_dict):
        self.track_id = song_dict['trackId']
        self.track_name = song_dict['trackName']
        self.track_number = song_dict['trackNumber']
        self.genre = song_dict['primaryGenreName']
        self.track_url = song_dict['trackViewUrl']

        self.album_id = song_dict['collectionId']
        self.album_name = song_dict['collectionName']
        self.album_url = song_dict['collectionViewUrl']

        self.artist_id = song_dict['artistId']
        self.artist_name = song_dict['artistName']
        self.artist_url = song_dict['artistViewUrl']

    def get_song_dict(self):
        return {
            'track_id': self.track_id,
            'track_name': self.track_name,
            'track_number': self.track_number,
            'genre': self.genre,
            'track_url': self.track_url,
            'artist_id': self.artist_id,
            'album_id': self.album_id
        }

    def get_artist_dict(self):
        return {

        }

    def get_album_dict(self):
        return {

        }


# the new stuff ------------------------------------------------------
def get_connection_and_cursor():
    global db_connection, db_cursor
    if not db_connection:
        try:
            db_connection = psycopg2.connect("dbname='{0}' user='{1}' password='{2}'".format(db_name, db_user, db_password))
            print("Success connecting to database")
        except:
            print("Unable to connect to the database. Check server and credentials.")
            sys.exit(1) # Stop running program if there's no db connection.

    if not db_cursor:
        db_cursor = db_connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    return db_connection, db_cursor

def setup_database():
    conn, cur = get_connection_and_cursor()

    # cur.execute("DROP TABLE IF EXISTS Songs")
    cur.execute("""CREATE TABLE IF NOT EXISTS Songs (
            track_id INTEGER PRIMARY KEY,
            track_name VARCHAR(255) NOT NULL,
            track_number INTEGER,
            genre VARCHAR(128),
            track_url TEXT,
            artist_id INTEGER,
            album_id INTEGER
        )""")

    # try using artist_id INTEGER REFERENCES Artists(artist_id)
    # try using album_id INTEGER REFERENCES Albums(album_id)

    # cur.execute("DROP TABLE IF EXISTS Albums")
    cur.execute("""CREATE TABLE IF NOT EXISTS Albums (
            album_id INTEGER PRIMARY KEY,
            album_name VARCHAR(255) NOT NULL,
            album_url TEXT
        )""")

    # cur.execute("DROP TABLE IF EXISTS Artists")
    cur.execute("""CREATE TABLE IF NOT EXISTS Artists (
            artist_id INTEGER PRIMARY KEY,
            artist_name VARCHAR(255) NOT NULL,
            artist_url TEXT
        )""")

    conn.commit()

    print('Setup database complete')

def insert(conn, cur, table, data_dict):
    column_names = data_dict.keys()
    # if DEBUG:
    #     print(column_names)

    # generate insert into query string
    query = sql.SQL('INSERT INTO {0}({1}) VALUES({2}) ON CONFLICT DO NOTHING').format(
        sql.SQL(table),
        sql.SQL(', ').join(map(sql.Identifier, column_names)),
        sql.SQL(', ').join(map(sql.Placeholder, column_names))
    )
    query_string = query.as_string(conn)
    cur.execute(query_string, data_dict)

def lookup_id(id):
    response = sample_get_cache_itunes_data(
        baseurl = "https://itunes.apple.com/lookup",
        params = { "id": id }
    )
    results = response['results']
    return results[0]

def search_songs(search_term):
    response = sample_get_cache_itunes_data(
        baseurl = "https://itunes.apple.com/search",
        params = {
            "term": search_term,
            "media": "music"
        }
    )
    results = response['results']
    if DEBUG:
        print(results)

    conn, cur = get_connection_and_cursor()
    for song_dict in results:
        song_object = Song(song_dict)
        cur.execute("""INSERT INTO
            Songs(track_id, track_name, track_number, genre, track_url, artist_id, album_id)
            values(%(track_id)s, %(track_name)s, %(track_number)s, %(genre)s, %(track_url)s, %(artist_id)s, %(album_id)s)
            on conflict do nothing""", song_object.get_song_dict())

        # insert(conn, cur, 'Songs', song_object.get_song_dict())
        # insert(conn, cur, 'Artists', song_object.get_artist_dict())
        # insert(conn, cur, 'Albums', song_object.get_album_dict())

    cur.execute("SELECT * FROM Songs")
    # print(cur.fetchall())
    for song_row in cur.fetchall():
        print(song_row)
    conn.commit()

if __name__ == '__main__':
    command = None
    search_term = None
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if len(sys.argv) > 2:
            search_term = sys.argv[2]

    if command == 'setup':
        print('setting up database')
        setup_database()
    elif command == 'search':
        load_cache()
        print('searching', search_term)
        search_songs(search_term)
    else:
        print('nothing to do')
