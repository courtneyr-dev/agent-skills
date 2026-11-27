-- SYNTHETIC FIXTURE: Fixture Co tenant-a schema v1 to v2. Adds a slug column and an index; keeps every row.
-- expect-column: posts.slug
-- expect-rows-unchanged: posts, comments
-- expect-rows: options=2
ALTER TABLE posts ADD COLUMN slug TEXT;
UPDATE posts SET slug = lower(replace(title, ' ', '-'));
CREATE INDEX posts_slug ON posts(slug);
UPDATE options SET value = '2' WHERE name = 'schema_version';
