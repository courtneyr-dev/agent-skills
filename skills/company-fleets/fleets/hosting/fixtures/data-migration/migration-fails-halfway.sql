-- SYNTHETIC FIXTURE: a v1 to v2 migration whose third statement references a missing table, so it fails after two statements changed data.
-- expect-column: posts.slug
-- expect-rows-unchanged: posts, comments
-- expect-rows: options=2
ALTER TABLE posts ADD COLUMN slug TEXT;
UPDATE posts SET slug = lower(replace(title, ' ', '-'));
INSERT INTO post_slugs (post_id, slug) SELECT id, slug FROM posts;
UPDATE options SET value = '2' WHERE name = 'schema_version';
