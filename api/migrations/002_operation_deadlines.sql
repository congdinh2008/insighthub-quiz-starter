ALTER TABLE operation_records ADD COLUMN IF NOT EXISTS deadline_at TIMESTAMPTZ;
UPDATE operation_records SET deadline_at = created_at + interval '120 seconds' WHERE deadline_at IS NULL;
ALTER TABLE operation_records ALTER COLUMN deadline_at SET NOT NULL;
ALTER TABLE operation_records ALTER COLUMN deadline_at SET DEFAULT (now() + interval '120 seconds');
CREATE INDEX IF NOT EXISTS operations_processing_deadline_idx ON operation_records(deadline_at) WHERE status='processing';
