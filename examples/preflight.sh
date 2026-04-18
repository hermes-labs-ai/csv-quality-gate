#!/usr/bin/env bash
set -euo pipefail

csv-quality-gate check leads.csv --profile outreach
