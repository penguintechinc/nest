"""Library-shaped adapters for penguin-libs packages not yet published to the index.

Only packages that fail ``scripts/probe-penguin-libs.sh`` get a module here; callers
import the same names the published library would provide so the adapter can be
deleted once the library ships.
"""
