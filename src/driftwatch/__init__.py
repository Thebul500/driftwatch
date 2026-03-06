"""driftwatch — Infrastructure drift detector. Snapshots Docker configs, crontabs, firewall rules, and package versions. Alerts via Signal when anything changes unexpectedly. Stores baselines in SQLite, diffs on schedule."""

__version__ = "0.1.0"
