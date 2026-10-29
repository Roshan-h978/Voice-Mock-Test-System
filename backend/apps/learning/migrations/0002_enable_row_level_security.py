"""On PostgreSQL (Supabase), switch on row-level security for the new tables.

Supabase publishes every table in the public schema through its Data API; with RLS on and no policies,
that API can't read them. Django connects as the table owner, so the app itself is not affected.
"""

from django.db import migrations

TABLES = ["learning_practiceanswer", "learning_notebookmark"]


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [("learning", "0001_initial")]

    operations = [migrations.RunPython(enable_rls, migrations.RunPython.noop)]
