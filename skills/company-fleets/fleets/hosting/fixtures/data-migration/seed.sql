-- SYNTHETIC FIXTURE: Fixture Co tenant-a site database seed (schema v1). No real people or orders.
CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, published INTEGER NOT NULL DEFAULT 0);
CREATE TABLE comments (id INTEGER PRIMARY KEY, post_id INTEGER NOT NULL REFERENCES posts(id), author_role TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE options (name TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT INTO posts VALUES (1, 'Welcome to Client A', 'Synthetic launch post.', 1);
INSERT INTO posts VALUES (2, 'Spring catalog', 'Synthetic catalog notes with unicode: café, naïve.', 1);
INSERT INTO posts VALUES (3, 'Draft pricing page', 'Synthetic draft.', 0);
INSERT INTO comments VALUES (1, 1, 'visitor', 'Synthetic comment one.');
INSERT INTO comments VALUES (2, 1, 'editor', 'Synthetic reply.');
INSERT INTO comments VALUES (3, 2, 'visitor', 'Synthetic question about the catalog.');
INSERT INTO options VALUES ('site_name', 'Client A (fixture)');
INSERT INTO options VALUES ('schema_version', '1');
