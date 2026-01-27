#!/bin/bash
#
# Unified SLURM submission script for Participatory Budgeting experiments
#
# Usage:
#   ./submit_pb.sh -a <algorithm> -u <utility> -c <completion> [-e] -d <data_dir>
#
# Arguments:
#   -a, --algorithm     Algorithm: ees or mes
#   -u, --utility       Utility type: cardinal or cost
#   -c, --completion    Completion method: none, add-one, add-opt, add-opt-skip
#   -e, --exhaustive    Enable exhaustive mode (continue until all projects selected)
#   -d, --data-dir      Directory containing .pb files to process
#   -p, --partition     SLURM partition (default: long)
#   -t, --time          Time limit (default: 01:00:00)
#   -o, --output-dir    Output directory for logs (default: result_logs)
#   -s, --script-dir    Directory containing run_pb.py (auto-detected)
#   -h, --help          Show this help message
#
# Examples:
#   # EES with cardinal utilities and ADD-OPT completion
#   ./submit_pb.sh -a ees -u cardinal -c add-opt -d /path/to/data
#
#   # MES with cost utilities, exhaustive mode
#   ./submit_pb.sh -a mes -u cost -c add-one -e -d /path/to/data
#
#   # EES with ADD-OPT-SKIP heuristic
#   ./submit_pb.sh -a ees -u cardinal -c add-opt-skip -d /path/to/data
#

set -e

# Default values
ALGORITHM=""
UTILITY=""
COMPLETION=""
EXHAUSTIVE=""
DATA_DIR=""
PARTITION="long"
TIME_LIMIT="01:00:00"
OUTPUT_DIR="result_logs"
SCRIPT_DIR=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--algorithm)
            ALGORITHM="$2"
            shift 2
            ;;
        -u|--utility)
            UTILITY="$2"
            shift 2
            ;;
        -c|--completion)
            COMPLETION="$2"
            shift 2
            ;;
        -e|--exhaustive)
            EXHAUSTIVE="--exhaustive"
            shift
            ;;
        -d|--data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        -p|--partition)
            PARTITION="$2"
            shift 2
            ;;
        -t|--time)
            TIME_LIMIT="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -s|--script-dir)
            SCRIPT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            head -40 "$0" | tail -35
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$ALGORITHM" ]] || [[ -z "$UTILITY" ]] || [[ -z "$COMPLETION" ]] || [[ -z "$DATA_DIR" ]]; then
    echo "Error: Missing required arguments"
    echo "Usage: $0 -a <algorithm> -u <utility> -c <completion> -d <data_dir>"
    echo "Run '$0 --help' for more information"
    exit 1
fi

# Validate algorithm
if [[ "$ALGORITHM" != "ees" ]] && [[ "$ALGORITHM" != "mes" ]]; then
    echo "Error: Algorithm must be 'ees' or 'mes', got: $ALGORITHM"
    exit 1
fi

# Validate utility
if [[ "$UTILITY" != "cardinal" ]] && [[ "$UTILITY" != "cost" ]]; then
    echo "Error: Utility must be 'cardinal' or 'cost', got: $UTILITY"
    exit 1
fi

# Validate completion
if [[ "$COMPLETION" != "none" ]] && [[ "$COMPLETION" != "add-one" ]] && [[ "$COMPLETION" != "add-opt" ]] && [[ "$COMPLETION" != "add-opt-skip" ]]; then
    echo "Error: Completion must be 'none', 'add-one', 'add-opt', or 'add-opt-skip', got: $COMPLETION"
    exit 1
fi

# MES only supports none and add-one
if [[ "$ALGORITHM" == "mes" ]] && [[ "$COMPLETION" != "none" ]] && [[ "$COMPLETION" != "add-one" ]]; then
    echo "Error: MES only supports 'none' or 'add-one' completion methods"
    exit 1
fi

# Check data directory exists
if [[ ! -d "$DATA_DIR" ]]; then
    echo "Error: Data directory does not exist: $DATA_DIR"
    exit 1
fi

# Auto-detect script directory if not specified
if [[ -z "$SCRIPT_DIR" ]]; then
    # Try to find run_pb.py relative to this script
    SCRIPT_DIR="$(dirname "$(realpath "$0")")/../PB_scripts"
    if [[ ! -f "$SCRIPT_DIR/run_pb.py" ]]; then
        # Try common locations
        if [[ -f "/data/coml-humanchess/univ5678/PB_scripts/run_pb.py" ]]; then
            SCRIPT_DIR="/data/coml-humanchess/univ5678/PB_scripts"
        else
            echo "Error: Cannot find run_pb.py. Use -s to specify script directory."
            exit 1
        fi
    fi
fi

RUN_PB_PATH="$SCRIPT_DIR/run_pb.py"
if [[ ! -f "$RUN_PB_PATH" ]]; then
    echo "Error: run_pb.py not found at: $RUN_PB_PATH"
    exit 1
fi

# Create output directory name based on configuration
EXHAUSTIVE_SUFFIX=""
if [[ -n "$EXHAUSTIVE" ]]; then
    EXHAUSTIVE_SUFFIX="_exhaustive"
fi
LOG_SUBDIR="${OUTPUT_DIR}/${ALGORITHM}_${UTILITY}_${COMPLETION}${EXHAUSTIVE_SUFFIX}"

# Create output directory
mkdir -p "$LOG_SUBDIR"

echo "=============================================="
echo "Submitting PB jobs with configuration:"
echo "  Algorithm:   $ALGORITHM"
echo "  Utility:     $UTILITY"
echo "  Completion:  $COMPLETION"
echo "  Exhaustive:  ${EXHAUSTIVE:-no}"
echo "  Data dir:    $DATA_DIR"
echo "  Script:      $RUN_PB_PATH"
echo "  Log dir:     $LOG_SUBDIR"
echo "  Partition:   $PARTITION"
echo "  Time limit:  $TIME_LIMIT"
echo "=============================================="

# Load necessary modules
module load Anaconda3 2>/dev/null || true

# Check/install dependencies
if ! python3 -c "import pandas" &> /dev/null; then
    echo "Installing pandas..."
    pip install --user pandas
fi

# Only check pabutools for MES
if [[ "$ALGORITHM" == "mes" ]]; then
    if ! python3 -c "import pabutools" &> /dev/null; then
        echo "Installing pabutools (required for MES)..."
        pip install --user pabutools
    fi
fi

# Count files
FILE_COUNT=$(find "$DATA_DIR" -maxdepth 1 -name "*.pb" -type f | wc -l)
echo "Found $FILE_COUNT .pb files to process"
echo ""

# Submit jobs
JOB_COUNT=0
for file in "$DATA_DIR"/*.pb; do
    if [[ -f "$file" ]]; then
        filename=$(basename -- "$file")
        job_name="${ALGORITHM}_${UTILITY}_${filename%.*}"

        # Build the command
        CMD="python3 $RUN_PB_PATH $file -a $ALGORITHM -u $UTILITY -c $COMPLETION $EXHAUSTIVE"

        # Submit job
        sbatch \
            --partition="$PARTITION" \
            --ntasks=1 \
            --cpus-per-task=1 \
            --time="$TIME_LIMIT" \
            --job-name="$job_name" \
            --output="$LOG_SUBDIR/${filename}.out" \
            --error="$LOG_SUBDIR/${filename}.err" \
            --wrap="$CMD"

        JOB_COUNT=$((JOB_COUNT + 1))
    fi
done

echo ""
echo "Submitted $JOB_COUNT jobs"
echo "Monitor with: squeue -u \$USER"
echo "Logs will be in: $LOG_SUBDIR"
