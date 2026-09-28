#!/usr/bin/env bash
set -euo pipefail

cd ~/godwyn-boss-fight

out="renders/astra/v3m_round2"
blend="models/astra_character_v3m_round2_wip.blend"
clips=(
  Combat_Stance Walk_Fight_Forward Attack Left_Slash Right_Hand_Sword_Slash
  Double_Combo_Attack Triple_Combo_Attack Sword_Judgment Reaping_Swing
  Rightward_Spin Basic_Jump Roll_Dodge Sword_Parry Hit_Reaction Dead
)

# Cycles can be evicted by the host after a short GPU burst.  The Blender
# renderer is deliberately resumable (it skips complete PNGs), so retry a
# killed chunk until the clip or sheet has a complete JSON receipt.
run_blender_resumable() {
  local receipt="$1"
  shift
  local attempt=1
  while [[ ! -s "$receipt" ]]; do
    if blender --background --python-exit-code 1 --python scripts/astra_v3m_render.py -- "$@"; then
      break
    else
      status=$?
    fi
    printf 'V3M_R2_RENDER_RETRY receipt=%s attempt=%s status=%s\n' "$receipt" "$attempt" "$status"
    attempt=$((attempt + 1))
    if (( attempt > 30 )); then
      printf 'V3M_R2_RENDER_ABORT receipt=%s attempts=%s\n' "$receipt" "$attempt" >&2
      return 1
    fi
  done
}

for clip in "${clips[@]}"; do
  run_blender_resumable "$out/render_film_${clip}.json" \
    film "$clip" --blend "$blend" --samples 2 --step 2 --out "$out"

  render_json="$out/render_film_${clip}.json"
  source_frames=$(jq -r '.source_frames' "$render_json")
  rendered_frames=$(jq -r '.rendered_frames' "$render_json")
  frame_dir="$out/${clip}_frames"
  if [[ ! -s "$out/${clip}.mp4" ]]; then
    ffmpeg -nostdin -hide_banner -loglevel warning -y -framerate 15 -i "$frame_dir/%04d.png" \
      -vf "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,tpad=stop_mode=clone:stop_duration=0.2" \
      -frames:v "$source_frames" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p \
      -movflags +faststart "$out/${clip}.mp4"
  fi
  if [[ ! -s "$out/${clip}_follow_sheet.png" ]]; then
    if compgen -G "$frame_dir/*.png" >/dev/null; then
      sheet_step=$(( (rendered_frames + 11) / 12 ))
      ffmpeg -nostdin -hide_banner -loglevel warning -y -framerate 15 -i "$frame_dir/%04d.png" \
        -vf "select='not(mod(n\,${sheet_step}))',scale=380:380:force_original_aspect_ratio=decrease,pad=384:384:(ow-iw)/2:(oh-ih)/2:black,tile=4x3:padding=4:margin=4" \
        -frames:v 1 -update 1 "$out/${clip}_follow_sheet.png"
    else
      sheet_step=$(( (source_frames + 11) / 12 ))
      ffmpeg -nostdin -hide_banner -loglevel warning -y -i "$out/${clip}.mp4" \
        -vf "select='not(mod(n\,${sheet_step}))',scale=380:380:force_original_aspect_ratio=decrease,pad=384:384:(ow-iw)/2:(oh-ih)/2:black,tile=4x3:padding=4:margin=4" \
        -frames:v 1 -update 1 "$out/${clip}_follow_sheet.png"
    fi
  fi

  if [[ -s "$out/render_sheet_${clip}.json" ]] && ! compgen -G "$out/${clip}_wide_frames/*.png" >/dev/null && [[ ! -s "$out/${clip}_contact_sheet.png" ]]; then
    rm "$out/render_sheet_${clip}.json"
  fi
  run_blender_resumable "$out/render_sheet_${clip}.json" \
    sheet "$clip" --blend "$blend" --samples 2 --out "$out"
  wide_dir="$out/${clip}_wide_frames"
  if [[ ! -s "$out/${clip}_contact_sheet.png" ]]; then
    ffmpeg -nostdin -hide_banner -loglevel warning -y -framerate 1 -i "$wide_dir/%04d.png" \
      -vf "scale=380:380:force_original_aspect_ratio=decrease,pad=384:384:(ow-iw)/2:(oh-ih)/2:black,tile=4x3:padding=4:margin=4" \
      -frames:v 1 -update 1 "$out/${clip}_contact_sheet.png"
  fi

  [[ ! -d "$frame_dir" ]] || find "$frame_dir" -type f -name '*.png' -delete
  [[ ! -d "$wide_dir" ]] || find "$wide_dir" -type f -name '*.png' -delete
  [[ ! -d "$frame_dir" ]] || rmdir "$frame_dir"
  [[ ! -d "$wide_dir" ]] || rmdir "$wide_dir"
  printf 'V3M_R2_FILM_PASS %s source_frames=%s rendered_frames=%s\n' "$clip" "$source_frames" "$rendered_frames"
done
