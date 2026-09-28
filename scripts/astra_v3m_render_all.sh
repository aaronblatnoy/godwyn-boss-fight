#!/usr/bin/env bash
set -euo pipefail

cd ~/godwyn-boss-fight

clips=(
  Combat_Stance Walk_Fight_Forward Attack Left_Slash Right_Hand_Sword_Slash
  Double_Combo_Attack Triple_Combo_Attack Sword_Judgment Reaping_Swing
  Rightward_Spin Basic_Jump Roll_Dodge Sword_Parry Hit_Reaction Dead
)

for clip in "${clips[@]}"; do
  if [[ -s "renders/astra/v3m/${clip}.mp4" && -s "renders/astra/v3m/${clip}_contact_sheet.png" ]]; then
    printf 'V3M_FILM_ALREADY_COMPLETE %s\n' "$clip"
    continue
  fi
  attempt=0
  until blender --background --python-exit-code 1 --python scripts/astra_v3m_render.py -- \
    film "$clip" --blend models/astra_character_v3m_wip.blend --samples 2 --step 2; do
    attempt=$((attempt + 1))
    if (( attempt >= 20 )); then
      printf 'V3M_FILM_ABORT %s retries=%s\n' "$clip" "$attempt" >&2
      exit 1
    fi
    printf 'V3M_FILM_RETRY %s attempt=%s\n' "$clip" "$attempt"
    sleep 2
  done
  render_json="renders/astra/v3m/render_film_${clip}.json"
  source_frames=$(jq -r '.source_frames' "$render_json")
  rendered_frames=$(jq -r '.rendered_frames' "$render_json")
  frame_dir="renders/astra/v3m/${clip}_frames"
  ffmpeg -nostdin -hide_banner -loglevel warning -y -framerate 15 -i "$frame_dir/%04d.png" \
    -vf "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,tpad=stop_mode=clone:stop_duration=0.2" \
    -frames:v "$source_frames" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p \
    -movflags +faststart "renders/astra/v3m/${clip}.mp4"
  sheet_step=$(( (rendered_frames + 11) / 12 ))
  ffmpeg -nostdin -hide_banner -loglevel warning -y -framerate 15 -i "$frame_dir/%04d.png" \
    -vf "select='not(mod(n\,${sheet_step}))',scale=380:380:force_original_aspect_ratio=decrease,pad=384:384:(ow-iw)/2:(oh-ih)/2:black,tile=4x3:padding=4:margin=4" \
    -frames:v 1 "renders/astra/v3m/${clip}_contact_sheet.png"
  rm -rf "$frame_dir"
  printf 'V3M_FILM_ENCODE_PASS %s source_frames=%s rendered_frames=%s\n' "$clip" "$source_frames" "$rendered_frames"
done
