DROP TABLE IF EXISTS version_info;
CREATE TABLE IF NOT EXISTS version_info (
    rowid integer primary key,
    version_date datetime default current_timestamp,
    narrative text );

DROP VIEW IF EXISTS current_version;
CREATE VIEW IF NOT EXISTS current_version AS
    SELECT ROWID, strftime('%s', VERSION_DATE) as unix_timestamp, narrative 
        FROM version_info 
        ORDER BY rowid DESC
        LIMIT 1;

INSERT INTO version_info (narrative) VALUES 
    ('This is the original version.');

DROP TABLE IF EXISTS metadata;
CREATE TABLE IF NOT EXISTS metadata (
    filename text,
    directory_name,
    inode integer,
    nlinks integer,
    filesize integer,
    mtime datetime,
    atime datetime,
    rowid integer primary key
    );

CREATE INDEX size_idx on metadata(filesize);
CREATE INDEX directory_idx on metadata(directory_name);

-- This view shows files with multiple hard links.
DROP VIEW IF EXISTS fake_duplicates;
CREATE VIEW fake_duplicates AS
    SELECT * FROM metadata WHERE nlinks > 1
        ORDER BY filename, directory_name;

-- This view shows files with the same size.
DROP VIEW IF EXISTS possible_duplicates;
CREATE VIEW possible_duplicates AS 
    SELECT t.* from metadata AS t
        INNER JOIN (
            SELECT filesize FROM metadata GROUP BY filesize 
            HAVING COUNT(*) > 1 )
        dups ON t.filesize = dups.filesize;

-- This view shows files with the same size and same name from
-- different directories. 
DROP VIEW IF EXISTS probable_duplicates;
CREATE VIEW probable_duplicates AS 
    SELECT t.* from metadata AS t
        INNER JOIN (
            SELECT filesize FROM metadata GROUP BY filesize 
            HAVING COUNT(*) > 1 )
        dups ON t.filesize = dups.filesize
        INNER JOIN (
            SELECT filename FROM metadata GROUP BY filename
            HAVING COUNT(*) > 1 )
        samename ON t.filename = samename.filename;


DROP TABLE IF EXISTS hashes;
CREATE TABLE IF NOT EXISTS hashes (
    file_id integer references metadata(rowid) on delete cascade,
    hash_size integer default 0,
    hash text );

