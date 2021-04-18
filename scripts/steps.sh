debug(){
    if [[ "$DEBUG_RUN" != "" ]]; then
        printf "run.sh-debug: %b\n" "$1"
    fi
}
info(){
    #printf "run.sh-info: %b (%s)\n" "$1" "$(date)"
    printf "run.sh-info: %b\n" "$1"
}
step(){
    _step=${1:?}
    debug "call: step $_step $run_steps"
    if grep -q $_step <<< $run_steps; then
        while read -r line
        do
            info "$_step> $(xargs <<< $line)"
            eval "$line"
        done < /dev/stdin
    fi
}

debug "steps.sh steps: ${steps[*]}"
from_flag_arg=${steps[0]}
to_flag_arg=${steps[-1]}
debug "steps.sh default from_flag_arg: $from_flag_arg"
debug "steps.sh default to_flag_arg: $to_flag_arg"

args="$@"
debug "steps.sh args: $args #=$#"
unset args

PARAMS=""

while (( "$#" )); do
  debug "args parse loop: $1"
  case "$1" in
    -from)
      if [ -n "$2" ] && [ ${2:0:1} != "-" ]; then
        from_flag_arg=$2
      else
        echo "Error: Argument for $1 is missing" >&2
        exit 1
      fi
      shift
      ;;
    -to)
      if [ -n "$2" ] && [ ${2:0:1} != "-" ]; then
        to_flag_arg=$2
        shift 2
      else
        echo "Error: Argument for $1 is missing" >&2
        exit 1
      fi
      ;;
    -*|--*=) # unsupported flags
      echo "Error: Unsupported flag $1" >&2
      exit 1
      ;;
    *) # preserve positional arguments
      PARAMS="$PARAMS $1"
      shift
      ;;
  esac
done

eval set -- "$PARAMS"

if ! grep -q $from_flag_arg <<< ${steps[*]}; then
  echo "Error: Invalid -from step: ${steps[*]}" >&2
  exit 1
fi
if ! grep -q $to_flag_arg <<< ${steps[*]}; then
  echo "Error: Invalid -to step: ${steps[*]}" >&2
  exit 1
fi
debug "steps.sh from_flag_arg: $from_flag_arg"
debug "steps.sh to_flag_arg: $to_flag_arg"

run_steps=$(echo ${steps[*]} | sed -r "s/^.*$from_flag_arg/$from_flag_arg/" \
    | sed -r "s/$to_flag_arg.*$/$to_flag_arg/")

info "Running steps: $run_steps"
