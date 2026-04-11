"""Delete files from Django storage (e.g. S3) by path."""


def delete_stored_file(fieldfile):
    """
    Remove the file at fieldfile's path from storage.

    Uses storage.delete(name) so the previous object is removed when replacing an
    upload, without relying on FieldFile.delete() side effects. Safe if empty.
    """
    if not fieldfile:
        return
    name = getattr(fieldfile, "name", "") or ""
    if not name:
        return
    storage = getattr(fieldfile, "storage", None)
    if not storage:
        return
    try:
        storage.delete(name)
    except Exception:
        pass


def clear_missing_file_fields(instance, *field_names):
    """
    Set nullable FileField/ImageField values to None when the object is gone
    from storage (e.g. deleted from S3 but DB path remains).
    """
    for attname in field_names:
        ff = getattr(instance, attname, None)
        if not ff or not getattr(ff, "name", ""):
            continue
        # New form uploads are not written to storage until model save (pre_save).
        # exists() is false for those paths — clearing here would drop the upload.
        if getattr(ff, "_committed", True) is False:
            continue
        storage = getattr(ff, "storage", None)
        if not storage:
            continue
        try:
            if not storage.exists(ff.name):
                setattr(instance, attname, None)
        except Exception:
            pass
