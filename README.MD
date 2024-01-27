# Tidal to Deezer Data Transfer

This Python script allows you to transfer playlists, artists, albums, and loved tracks from Tidal to Deezer.
It uses the Tidal and Deezer Python APIs to fetch the necessary data and perform the transfer.
It stores the Deezer and Tidal access tokens by creating a `credentials.json` file, so you don't have to re-authenticate every time you run the script.
You can filter a Tidal playlist by name to transfer only these using `namefilter.txt`.
You can also choose to remove the Tidal playlist after transferring it to Deezer.

## Prerequisites

Before running the script, make sure you have the following:

- Python 3.x installed
- Library Requirements: `pip install -r requirements.txt`
- Tidal and Deezer accounts (of course)
- Deezer API credentials (stored in `credentials_deezer.json`) which can be obtained by following the instructions in the [official website](https://developers.deezer.com/myapps)

the file `credentials_deezer.json` should be like this:

```example
{
  "DEEZER_SECRET_TOKEN": "xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "DEEZER_APP_ID": "xxxxxx"
}
```

## Installation

1. Clone the repository:

   ```shell
   git clone https://github.com/siloli/Tidal-to-Deezer.git
   ```

2. Install the required Python packages:

   ```shell
   pip install -r requirements.txt
   ```

3. Fill the `credentials_deezer.json` file in the root directory of the project and add your Deezer API credentials. (See [Prerequisites](#Prerequisites) for more details)

4. Read the [Usage](#Usage) section to customize the script.

5. Run the script:

   ```shell
   python tidal_to_deezer.py
   ```

## Usage

1. Customize the script:

   - Set the `REMOVE` variable to `True` if you want to remove the Tidal playlist after adding it to Deezer.
   - Modify the `namefilter.txt` file to filter the Tidal playlist by name. One playlist name per line.
   - Un/Comment the functions to choose which data to transfer :

     ```python
     #Here I don't want to transfer my loved tracks, so I comment the function

     get_tidal_tracks_from_playlist(
     boring arguments)
     get_tidal_artists(boring arguments)
     get_tidal_albums(boring arguments)
     #put hashtag in front of the function you don't want to use
     #get_tidal_loved_tracks(boring arguments) <-this one is deactivated here
     print("Done!")
     ```

2. Run the script:
   you can also run the script with optional namefilter.txt:

   ```shell
   # will use default_namefilter.txt
   python tidal_to_deezer.py

   # will use personalfilter.txt
   python tidal_to_deezer.py personalfilter.txt
   ```

3. Follow the instructions in the console to authenticate with Deezer and start the migration process.

## Limitations

- The script uses a rate limiter to comply with Deezer API rate limits (50 requests every 5 seconds).
- Some tracks, artists, albums, or playlists may not be found on Deezer due to differences in the catalogs of Tidal and Deezer.
- Errors encountered during the transfer process are logged in the `LogFile.txt` file.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Thanks

- [python-tidal](https://github.com/tamland/python-tidal)
- [deezer-python](https://github.com/browniebroke/deezer-python)
- [deezer-oauth-cli](https://github.com/browniebroke/deezer-oauth-cli)
