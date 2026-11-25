import gzip
import io
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import os

M3U_URL = os.getenv(
    "M3U_URL",
    "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/vn.m3u",
)
EPG_URL = os.getenv("EPG_URL", "https://lichphatsong.io.vn/epg.xml")
FALLBACK_EPG_FILE = Path("epg_fallback.xml")
OUTPUT_FILE = Path("output.m3u")

TVG_ID_MAP = {
    "AnNinhTV.vn@HD": "antvhd",
    "CaMauTV.vn@SD": "camau",
    "CanThoTV.vn@SD": "cantho1",
    "CanThoTV2.vn@SD": "cantho2",
    "CanThoTV3.vn@SD": "cantho3",
    "CaoBangTV.vn@SD": "caobang",
    "DaNangTV1.vn@SD": "danang1",
    "DaNangTV2.vn@SD": "danang2",
    "DakLakTV.vn@HD": "daklak",
    "DienBienTV.vn@SD": "dienbien",
    "DongNaiTV1.vn@SD": "dongnai1",
    "DongNaiTV2.vn@SD": "dongnai2",
    "DongThapTV.vn@SD": "dongthap1",
    "TienGiangTV.vn@SD": "dongthap2",
    "GiaLaiTV.vn@SD": "gialai",
    "HaTinhTV.vn@SD": "hatinh",
    "HanoiTV1.vn@SD": "hanoi1",
    "HTV1.vn@SD": "htv1",
    "HTV2.vn@HD": "htv2hd",
    "HTV3.vn@SD": "htv3",
    "HTV4.vn@HD": "htv4",
    "HTV5.vn@HD": "htv5",
    "HTV7.vn@HD": "htv7hd",
    "HTV7.vn@SD": "htv7hd",
    "HTV9.vn@SD": "htv9hd",
    "HTVSports.vn@SD": "htvthethaohd",
    "HTVCFamily.vn@SD": "htvcgiadinhhd",
    "HTVCMovies.vn@SD": "htvcphimhd",
    "HTVCWomen.vn@SD": "htvcphunuhd",
    "HungYenTV.vn@SD": "hungyen",
    "LangSonTV.vn@SD": "langson",
    "LaoCaiTV.vn@HD": "laocai",
    "NgheAnTV.vn@SD": "nghean",
    "NgheAnTV.vn@HD": "nghean",
    "ONBiBi.vn@SD": "onbibi",
    "ONCine.vn@SD": "oncine",
    "ONEChannel.vn@HD": "onechannel",
    "ONInfoTV.vn@SD": "oninfotv",
    "ONKids.vn@SD": "onkids",
    "ONLife.vn@SD": "onlife",
    "ONMovies.vn@SD": "onmovies",
    "ONMusic.vn@SD": "onmusic",
    "ONO2TV.vn@SD": "ono2tv",
    "ONPhimViet.vn@SD": "onphimviet",
    "ONStyleTV.vn@SD": "onstyle",
    "ONTrendingTV.vn@SD": "ontrending",
    "ONVFamily.vn@SD": "onvfamily",
    "ONVieDramas.vn@SD": "onviedramas",
    "ONVieGiaiTri.vn@HD": "onviegiaitri",
    "QPVN.vn@HD": "qpvnhd",
    "QuangNgaiTV.vn@HD": "quangngai",
    "SCTV2.vn@SD": "sctv2hd",
    "SCTV3.vn@SD": "sctv3hd",
    "SCTV4.vn@SD": "sctv4hd",
    "SCTV6.vn@SD": "sctv6hd",
    "SCTV7.vn@SD": "sctv7hd",
    "SCTV9.vn@SD": "sctv9hd",
    "SCTV11.vn@SD": "sctv11hd",
    "SCTV12.vn@SD": "sctv12hd",
    "SCTV13.vn@SD": "sctv13hd",
    "SCTV14.vn@SD": "sctv14hd",
    "SCTV16.vn@SD": "sctv16hd",
    "SCTV18.vn@SD": "sctv18hd",
    "SCTV19.vn@SD": "sctv19hd",
    "SCTV20.vn@SD": "sctv20hd",
    "TayNinhTV.vn@SD": "tayninh1",
    "ThaiNguyenTV.vn@SD": "thainguyen",
    "TVBVietnam.vn@SD": "tvbvn",
    "VietnamToday.vn@HD": "vietnamtoday",
    "VinhLongTV1.vn@SD": "vinhlong1hd",
    "VinhLongTV1.vn@HD": "vinhlong1hd",
    "VinhLongTV2.vn@SD": "vinhlong2hd",
    "VinhLongTV3.vn@SD": "vinhlong3hd",
    "VinhLongTV4.vn@SD": "vinhlong4hd",
    "VinhLongTV5.vn@SD": "vinhlong5hd",
    "VTV1.vn@HD": "vtv1hd",
    "VTV2.vn@HD": "vtv2hd",
    "VTV3.vn@HD": "vtv3hd",
    "VTV4.vn@HD": "vtv4hd",
    "VTV5.vn@HD": "vtv5hd",
    "VTV5TayNamBo.vn@HD": "vtv5hdtnb",
    "VTV5TayNguyen.vn@HD": "vtv5hdtn",
    "VTV6.vn@HD": "vtv6hd",
    "VTV7.vn@HD": "vtv7hd",
    "VTV8.vn@HD": "vtv8hd",
    "VTV9.vn@HD": "vtv9hd",
    "VTV10.vn@HD": "vtv10hd",
}

TITLE_FALLBACK_MAP = {
    "on vie drama": "onviedramas",
    "đồng tháp tv2": "dongthap2",
    "dong thap tv2": "dongthap2",
}


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/xml,text/xml,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://lichphatsong.io.vn/",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data


def parse_epg_channels(xml_bytes: bytes) -> dict[str, str]:
    channels: dict[str, str] = {}
    context = ET.iterparse(io.BytesIO(xml_bytes), events=("end",))
    for _, elem in context:
        if elem.tag == "channel":
            ch_id = (elem.attrib.get("id") or "").strip()
            if ch_id:
                icon_el = elem.find("icon")
                icon_src = ""
                if icon_el is not None:
                    icon_src = (
                        icon_el.attrib.get("src") or icon_el.attrib.get("url") or ""
                    ).strip()
                channels[ch_id] = icon_src
            elem.clear()
        elif elem.tag == "programme":
            elem.clear()
            if channels:
                break
    return channels


def normalize_key(text: str) -> str:
    return re.sub(r"\s*\([^)]*\)|\s*\[[^\]]*\]", "", text).strip().lower()


def resolve_epg_id(old_tvg_id: str, title: str, epg_channels: dict[str, str]) -> str:
    # Khi không tải được EPG online, vẫn giữ nguyên tvg-id gốc hoặc ánh xạ đã biết
    mapped_default = TVG_ID_MAP.get(old_tvg_id, old_tvg_id)
    if not epg_channels:
        return mapped_default

    if old_tvg_id in TVG_ID_MAP and TVG_ID_MAP[old_tvg_id] in epg_channels:
        return TVG_ID_MAP[old_tvg_id]

    if old_tvg_id and old_tvg_id in epg_channels:
        return old_tvg_id

    if old_tvg_id:
        base = re.sub(r"\.vn@(hd|sd)$", "", old_tvg_id, flags=re.IGNORECASE).lower()
        base_clean = re.sub(r"[^a-z0-9]", "", base)
        for cand in (base, base_clean, f"{base}hd", f"{base_clean}hd"):
            if cand in epg_channels:
                return cand

    clean_title = normalize_key(title)
    if clean_title in TITLE_FALLBACK_MAP and TITLE_FALLBACK_MAP[clean_title] in epg_channels:
        return TITLE_FALLBACK_MAP[clean_title]

    return mapped_default


def build_m3u(m3u_text: str, epg_channels: dict[str, str]) -> str:
    lines = [line.strip() for line in m3u_text.splitlines() if line.strip()]
    out_lines = ["#EXTM3U"]

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF:"):
            meta_part, title = line.split(",", 1) if "," in line else (line, "")
            title = title.strip()

            tvg_id_match = re.search(r'tvg-id="([^"]*)"', meta_part)
            old_tvg_id = tvg_id_match.group(1).strip() if tvg_id_match else ""

            matched_id = resolve_epg_id(old_tvg_id, title, epg_channels)
            logo_url = epg_channels.get(matched_id, "") if epg_channels else ""

            dur_match = re.match(r"^(#EXTINF:[^\s,]+)", meta_part)
            prefix = dur_match.group(1) if dur_match else "#EXTINF:-1"

            new_extinf = f'{prefix} tvg-id="{matched_id}" tvg-logo="{logo_url}",{title}'

            stream_url = ""
            if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                stream_url = lines[i + 1]
                i += 1

            if stream_url:
                out_lines.append(new_extinf)
                out_lines.append(stream_url)
        i += 1

    return "\n".join(out_lines) + "\n"


def main():
    print("Đang tải M3U và EPG...")
    try:
        m3u_text = fetch_bytes(M3U_URL).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Lỗi khi tải M3U: {e}", file=sys.stderr)
        sys.exit(1)

    epg_channels: dict[str, str] = {}
    try:
        epg_bytes = fetch_bytes(EPG_URL)
        epg_channels = parse_epg_channels(epg_bytes)
        print(f"Đã đọc {len(epg_channels)} kênh từ EPG.")
    except urllib.error.HTTPError as e:
        print(f"Cảnh báo: Không tải được EPG (HTTP {e.code} {e.reason}).", file=sys.stderr)
    except Exception as e:
        print(f"Cảnh báo: Lỗi xử lý EPG ({e}).", file=sys.stderr)

    if not epg_channels and FALLBACK_EPG_FILE.exists():
        try:
            epg_channels = parse_epg_channels(FALLBACK_EPG_FILE.read_bytes())
            print(f"Đã đọc {len(epg_channels)} kênh từ {FALLBACK_EPG_FILE}.")
        except Exception as e:
            print(f"Cảnh báo: Không đọc được {FALLBACK_EPG_FILE} ({e}).", file=sys.stderr)

    result_m3u = build_m3u(m3u_text, epg_channels)
    OUTPUT_FILE.write_text(result_m3u, encoding="utf-8")
    print(f"Hoàn tất! Đã xuất file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
