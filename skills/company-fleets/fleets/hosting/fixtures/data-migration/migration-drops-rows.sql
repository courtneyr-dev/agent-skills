-- SYNTHETIC FIXTURE: a migration that runs without an error but silently deletes the unpublished post; the row-count post-condition must catch it.
-- expect-column: posts.slug
-- expect-rows-unchanged: posts, comments, options
ALTER TABLE posts ADD COLUMN slug TEXT;
UPDATE posts SET slug = lower(replace(title, ' ', '-'));
DELETE FROM posts WHERE published = 0;
