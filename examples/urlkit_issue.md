append_query silently loses query parameters.

Existing URLs may have repeated keys such as tag=a&tag=b, or empty values such as
empty=. These entries must be retained in their original order. New parameters
must be appended, even when their keys already exist in the URL. Accept either a
mapping or a sequence of key/value pairs; sequences may contain repeated keys.
Preserve the scheme, host, path and fragment. Keep using standard query encoding.
Reproduce the issue, fix the implementation and run the repository tests.
