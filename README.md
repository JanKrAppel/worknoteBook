# worknoteBook

worknoteBook is a CherryPy based web server and command-line client intended to store multiple ET/worknote objects. It allows for structured storage in subdirectories called chapters and full-text searching in the notes.

**Although upload and deletion of Worknotes is password protected, this server should in no way be considered secure. The password protection is only to stop ~~colleagues~~ you from deleting your notes. It can probably be trivially broken or circumvented.**

## Installation

### Prerequisites

worknoteBook uses the Worknote class which you'll need to have available in ```$PYTHONPATH```. In addition, it uses the following Python modules:

#### Server

- CherryPy
- Whoosh

#### Client

The client should be able to run with only the standard libraries.

## Usage

All functionality can be used by the ```worknoteBook``` command. A list of common operations is:

```worknoteBook server``` starts the server. For default config, see [server.cfg.example](server.cfg.example) or place an appropriately edited copy to ```~/.worknoteBook/server.cfg```. The default user/pass given in the [users.dat.example](users.dat.example) is ```user``` with the password ```pass```. Passwords should be stored as simple md5 hashes.

The client stores a list of servers and can be set to use a default server. For default config, see [client.cfg.example](client.cfg.example) or place an appropriately edited copy in ```~/.worknoteBook/client.cfg```. Each server has an URL, a port and an alias. If no server alias is given in the command, the default server is used. To use another server, use the ```--server``` or ```-s``` option:
```worknoteBook --server <alias>```
Some common operations would be:
```worknoteBook list``` List all worknotes
```worknoteBook download -index <index>``` Download the worknote at the given index
```worknoteBook upload -w <worknote> [-c <chapter>]``` Upload the worknote to the given chapter. If no chapter is given, the default storage dir is used.
```worknoteBook delete -i <index>``` Delete the worknote at the given index

The full help output is:
```
usage: worknoteBook [-h] [--index INDEX] [--workdir WORKDIR] [--overwrite]
                    [--server SERVER] [--url URL] [--port PORT]
                    [--chapter CHAPTER] [--query QUERY] [--user USER]
                    [--password PASSWORD]
                    
                    {server,list,download,upload,add_server,set_default_server,search,delete}

positional arguments:
  {server,list,download,upload,add_server,set_default_server,search,delete}
                        Command to execute

optional arguments:
  -h, --help            show this help message and exit
  --index INDEX, -i INDEX
                        Select the index
  --workdir WORKDIR, -w WORKDIR
                        Select the working directory
  --overwrite, -o       Overwrite worknote, if present
  --server SERVER, -s SERVER
                        Set the server name
  --url URL             Set the server URL
  --port PORT           Set the server port
  --chapter CHAPTER, -c CHAPTER
                        Chapter to upload worknote to
  --query QUERY, -q QUERY
                        String to search for
  --user USER           Set the username
  --password PASSWORD   Set the password
  ```