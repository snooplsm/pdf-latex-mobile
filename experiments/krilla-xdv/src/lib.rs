mod pdf_code;
mod safe_surface;
mod tfm;
#[cfg(test)]
mod xdv_tests;
// Experimental native-glyph XDV backend. Unsupported operations are errors.
use anyhow::{Context, Result, bail};
use krilla::{
    Document,
    color::{Color, rgb, cmyk},
    geom::{PathBuilder, Point, Rect, Size, Transform},
    page::PageSettings,
    paint::Fill,
    pdf::{Pdf, PdfDocument},
    text::{Font, GlyphId, KrillaGlyph},
};
use std::{collections::BTreeMap, path::PathBuf};
use tectonic_xdv::{XdvEvents, XdvParser};

enum Op {
    Glyphs(i32, Vec<u16>, Vec<i32>, Vec<i32>),
    Rule(i32, i32, i32, i32),
    Special(i32, i32, String),
}
struct Page {
    ops: Vec<Op>,
    width: f32,
    height: f32,
}
#[derive(Default)]
struct Input {
    pages: Vec<Page>,
    fonts: BTreeMap<i32, (String, i32, u32)>,
    font_dir: PathBuf,
    traditional: BTreeMap<i32, (tfm::Metrics, BTreeMap<i32, (u16, String)>)>,
}
impl XdvEvents for Input {
    type Error = anyhow::Error;
    fn handle_define_font(
        &mut self,
        number: i32,
        _checksum: u32,
        size: u32,
        _design: u32,
        area: &str,
        name: &str,
    ) -> Result<()> {
        if !area.is_empty() || name.contains('/') || name.contains('\\') || name.contains("..") {
            bail!("invalid traditional font name");
        }
        let metrics = tfm::Metrics::parse(
            &std::fs::read(self.font_dir.join(format!("{name}.tfm")))?,
            size,
        )?;
        let encoding: serde_json::Value = serde_json::from_slice(&std::fs::read(
            self.font_dir.join(format!("{name}.encoding.json")),
        )?)?;
        let mut mapping = BTreeMap::new();
        for entry in encoding.as_array().context("invalid font encoding")? {
            let code = i32::try_from(entry["code"].as_i64().context("missing character code")?)?;
            let gid = u16::try_from(entry["gid"].as_u64().context("missing glyph id")?)?;
            mapping.insert(
                code,
                (
                    gid,
                    entry["text"]
                        .as_str()
                        .context("missing glyph text")?
                        .to_owned(),
                ),
            );
        }
        let renames: BTreeMap<String, String> =
            serde_json::from_str(include_str!("../font-renames.json"))?;
        let converted = renames
            .get(name)
            .context("font has no converted counterpart")?;
        self.fonts
            .insert(number, (converted.clone(), i32::try_from(size)?, 0));
        self.traditional.insert(number, (metrics, mapping));
        Ok(())
    }
    fn handle_character(&mut self, f: i32, c: i32, x: i32, y: i32) -> Result<i32> {
        let (metrics, mapping) = self
            .traditional
            .get(&f)
            .context("undefined traditional font")?;
        let (gid, text) = mapping.get(&c).context("unmapped traditional character")?;
        if text.is_empty() {
            bail!("traditional character {c} lacks Unicode mapping");
        }
        let advance = metrics.width(c)?;
        self.pages
            .last_mut()
            .context("character outside page")?
            .ops
            .push(Op::Glyphs(f, vec![*gid], vec![x], vec![y]));
        Ok(advance)
    }
    fn handle_begin_page(&mut self, _: &[i32], _: i32) -> Result<()> {
        self.pages.push(Page {
            ops: vec![],
            width: 612.0,
            height: 792.0,
        });
        Ok(())
    }
    fn handle_define_native_font(
        &mut self,
        name: &str,
        number: i32,
        size: i32,
        face: u32,
        color: Option<u32>,
        extend: Option<u32>,
        slant: Option<u32>,
        embolden: Option<u32>,
    ) -> Result<()> {
        if color.is_some() || extend.is_some() || slant.is_some() || embolden.is_some() {
            bail!("unsupported native font effects");
        }
        self.fonts.insert(number, (name.into(), size, face));
        Ok(())
    }
    fn handle_glyph_run(&mut self, f: i32, glyphs: &[u16], x: &[i32], y: &[i32]) -> Result<()> {
        self.pages
            .last_mut()
            .context("glyph outside page")?
            .ops
            .push(Op::Glyphs(f, glyphs.to_vec(), x.to_vec(), y.to_vec()));
        Ok(())
    }
    fn handle_text_and_glyphs(
        &mut self,
        _: i32,
        _: &str,
        _: i32,
        _: &[u16],
        _: &[i32],
        _: &[i32],
    ) -> Result<()> {
        bail!("text-and-glyph command not yet implemented")
    }
    fn handle_char_run(&mut self, _: i32, _: &[i32]) -> Result<()> {
        bail!("traditional TeX font rendering not yet implemented")
    }
    fn handle_rule(&mut self, x: i32, y: i32, h: i32, w: i32) -> Result<()> {
        self.pages
            .last_mut()
            .context("rule outside page")?
            .ops
            .push(Op::Rule(x, y, h, w));
        Ok(())
    }
    fn handle_special(&mut self, x: i32, y: i32, data: &[u8]) -> Result<()> {
        let text = std::str::from_utf8(data)?;
        if text == "pdf:pagesize default" || text == "pdfcolorstackinit 1 page direct (0 g 0 G)" {
            return Ok(());
        }
        let page = self.pages.last_mut().context("special outside page")?;
        if let Some(dims) = text.strip_prefix("pdf:pagesize width ") {
            let (w, h) = dims
                .split_once(" height ")
                .context("invalid page dimensions")?;
            page.width = (w
                .strip_suffix("pt")
                .context("unsupported page unit")?
                .parse::<f64>()?
                * 72.0
                / 72.27) as f32;
            page.height = (h
                .strip_suffix("pt")
                .context("unsupported page unit")?
                .parse::<f64>()?
                * 72.0
                / 72.27) as f32;
            if !page.width.is_finite()
                || !page.height.is_finite()
                || page.width <= 0.0
                || page.height <= 0.0
            {
                bail!("invalid page size");
            }
        } else {
            page.ops.push(Op::Special(x, y, text.into()));
        }
        Ok(())
    }
}
fn asset_path(root: &std::path::Path, name: &str) -> Result<PathBuf> {
    use std::path::Component;
    let path = std::path::Path::new(name);
    if name.is_empty()
        || name.contains('\\')
        || name.contains(':')
        || name.contains('\0')
        || name
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
        || !path
            .components()
            .all(|part| matches!(part, Component::Normal(_)))
    {
        bail!("invalid image path");
    }
    let root = root.canonicalize()?;
    let resolved = root.join(path).canonicalize()?;
    if !resolved.starts_with(&root) || !resolved.is_file() {
        bail!("image is outside asset directory or not a file");
    }
    Ok(resolved)
}

fn channel(value: &str) -> Result<f32> {
    let v = value.parse::<f32>()?;
    if !v.is_finite() || !(0.0..=1.0).contains(&v) {
        bail!("invalid color channel");
    }
    Ok(v)
}
fn parse_color_components(parts: &[&str]) -> Result<Color> {
    Ok(match parts {
        [v] => {
            let v = channel(v)?;
            rgb::Color::new_normalized(v, v, v).context("invalid gray")?.into()
        }
        [r, g, b] => rgb::Color::new_normalized(channel(r)?, channel(g)?, channel(b)?)
            .context("invalid RGB")?.into(),
        [c, m, y, k] => cmyk::Color::new_normalized(channel(c)?, channel(m)?, channel(y)?, channel(k)?)
            .context("invalid CMYK")?.into(),
        _ => bail!("unsupported color component count"),
    })
}

fn bp(value: i32) -> f32 {
    (f64::from(value) * 72.0 / 72.27 / 65536.0) as f32
}
/// Render XDV from a seekable input using explicit bundled fonts and optional assets.
/// The PDF builder currently returns an in-memory document; inputs may be files or cursors.
pub fn render<R: std::io::Read + std::io::Seek>(
    input: R,
    font_dir: &std::path::Path,
    asset_dir: Option<&std::path::Path>,
) -> Result<Vec<u8>> {
    let input = XdvParser::process_with_seeks(
        input,
        Input {
            font_dir: font_dir.to_owned(),
            ..Input::default()
        },
    )?;
    let mut fonts = BTreeMap::new();
    for (&id, (name, size, face)) in &input.fonts {
        if name.contains('/') || name.contains('\\') || name.contains("..") {
            bail!("invalid font name");
        }
        let bytes = std::fs::read(font_dir.join(
            if name.ends_with(".otf") || name.ends_with(".ttf") {
                name.clone()
            } else {
                format!("{name}.otf")
            },
        ))?;
        let parsed = ttf_parser::Face::parse(&bytes, *face)?;
        let mut unicode = BTreeMap::new();
        if let Some(cmap) = parsed.tables().cmap {
            for subtable in cmap.subtables.into_iter().filter(|s| s.is_unicode()) {
                subtable.codepoints(|cp| {
                    if let (Some(ch), Some(gid)) = (char::from_u32(cp), subtable.glyph_index(cp)) {
                        unicode.entry(gid.0).or_insert_with(|| match ch {
                            '\u{fb00}' => "ff".into(),
                            '\u{fb01}' => "fi".into(),
                            '\u{fb02}' => "fl".into(),
                            '\u{fb03}' => "ffi".into(),
                            '\u{fb04}' => "ffl".into(),
                            '\u{fb05}' | '\u{fb06}' => "st".into(),
                            _ => ch.to_string(),
                        });
                    }
                });
            }
        }
        let font = Font::new(bytes.into(), *face).context("invalid font")?;
        if let Some((_, mapping)) = input.traditional.get(&id) {
            for (gid, text) in mapping.values() {
                if !text.is_empty() {
                    unicode.insert(*gid, text.clone());
                }
            }
        }
        fonts.insert(id, (font, bp(*size), unicode));
    }
    let mut doc = Document::new();
    let mut colors: Vec<Color> = vec![rgb::Color::new(0, 0, 0).into()];
    for info in input.pages {
        let mut page = doc.start_page_with(
            // The page box is rounded, but the drawing origin must retain the
            // requested height or every mark on non-integer-sized pages shifts.
            PageSettings::from_wh(info.width, info.height)
                .context("invalid page dimensions")?
                .with_media_box(Some(
                    Rect::from_xywh(
                        0.0,
                        info.height - (info.height * 100.0).round() / 100.0,
                        (info.width * 100.0).round() / 100.0,
                        (info.height * 100.0).round() / 100.0,
                    )
                    .context("invalid media box")?,
                )),
        );
        let mut surface = safe_surface::SafeSurface::new(page.surface());
        surface.set_fill(Some(Fill {
            paint: colors.last().unwrap().clone().into(),
            ..Default::default()
        }));
        let mut scopes: Vec<usize> = vec![];
        let mut pdf_code = pdf_code::PdfCode::default();
        for op in info.ops {
            let (id, glyphs, xs, ys) = match op {
                Op::Glyphs(f, g, x, y) => (f, g, x, y),
                Op::Rule(x, y, h, w) => {
                    if h > 0 && w > 0 {
                        let mut path = PathBuilder::new();
                        path.push_rect(
                            Rect::from_xywh(72.0 + bp(x), 72.0 + bp(y) - bp(h), bp(w), bp(h))
                                .context("invalid rule")?,
                        );
                        surface.draw_path(&path.finish().context("invalid rule path")?);
                    }
                    continue;
                }
                Op::Special(x, y, s) => {
                    let s = if let Some(rest) = s.strip_prefix("pdf:") {
                        format!("pdf:{}", rest.trim_start())
                    } else {
                        s
                    };
                    if std::env::var_os("XDV_TRACE").is_some() {
                        eprintln!("{s}");
                    }
                    let px = 72.0 + bp(x);
                    let py = 72.0 + bp(y);
                    if s == "pdf:obj @pgfcolorspaces <<>>"
                        || s == "pdf:put @pgfcolorspaces <<  /pgfprgb [/Pattern /DeviceRGB]  >>"
                        || s == "pdf:put @resources << /ColorSpace @pgfcolorspaces >>"
                    {
                        // Resource declarations alone do not draw. Pattern-selection operators
                        // are rejected by the interpreter until pattern rendering is supported.
                    } else if s == "pdf:bcontent" {
                        pdf_code.begin(px, py);
                    } else if s == "pdf:econtent" {
                        pdf_code.end(&mut surface)?;
                    } else if let Some(code) = s.strip_prefix("pdf:code ") {
                        pdf_code.invoke(&mut surface, code)?;
                    } else if let Some(spec) = s
                        .strip_prefix("pdf:bcolor [")
                        .and_then(|s| s.strip_suffix(']'))
                    {
                        let c = parse_color_components(&spec.split_whitespace().collect::<Vec<_>>())?;
                        colors.push(c.clone());
                        surface.set_fill(Some(Fill {
                            paint: c.into(),
                            ..Default::default()
                        }));
                    } else if s == "pdf:ecolor" {
                        if colors.len() <= 1 {
                            bail!("color stack underflow");
                        }
                        colors.pop();
                        surface.set_fill(Some(Fill {
                            paint: colors.last().unwrap().clone().into(),
                            ..Default::default()
                        }));
                    } else if let Some(spec) = s.strip_prefix("color push ") {
                        let parts: Vec<_> = spec.split_whitespace().collect();
                        let c = match parts.as_slice() {
                            ["gray", v] => parse_color_components(&[v])?,
                            ["rgb", r, g, b] => parse_color_components(&[r, g, b])?,
                            ["cmyk", c, m, y, k] => parse_color_components(&[c, m, y, k])?,
                            _ => bail!("unsupported color {spec}"),
                        };
                        colors.push(c.clone());
                        surface.set_fill(Some(Fill {
                            paint: c.into(),
                            ..Default::default()
                        }));
                    } else if s == "color pop" {
                        if colors.len() <= 1 {
                            bail!("color stack underflow");
                        }
                        colors.pop();
                        surface.set_fill(Some(Fill {
                            paint: colors.last().unwrap().clone().into(),
                            ..Default::default()
                        }));
                    } else if s == "pdf:btrans" {
                        scopes.push(0);
                    } else if let Some(values) = s.strip_prefix("pdf:btrans matrix ") {
                        let values: Vec<f32> = values
                            .split_whitespace()
                            .map(str::parse)
                            .collect::<std::result::Result<_, _>>()?;
                        let [a, b, c, d, e, f]: [f32; 6] = values
                            .try_into()
                            .map_err(|_| anyhow::anyhow!("invalid transform matrix"))?;
                        if [a, b, c, d, e, f].iter().any(|v| !v.is_finite()) {
                            bail!("nonfinite transform");
                        }
                        surface.push_transform(&Transform::from_row(
                            a,
                            -b,
                            -c,
                            d,
                            px - a * px + c * py + e,
                            py + b * px - d * py - f,
                        ));
                        scopes.push(1);
                    } else if let Some(deg) = s.strip_prefix("pdf:btrans rotate ") {
                        let theta = -deg.parse::<f32>()?.to_radians();
                        let a = theta.cos();
                        let b = theta.sin();
                        let c = -b;
                        let d = a;
                        surface.push_transform(&Transform::from_row(
                            a,
                            b,
                            c,
                            d,
                            px - a * px - c * py,
                            py - b * px - d * py,
                        ));
                        scopes.push(1);
                    } else if let Some(scale) = s.strip_prefix("x:scale ") {
                        let (sx, sy) = scale.split_once(' ').context("invalid scale")?;
                        let sx = sx.parse::<f32>()?;
                        let sy = sy.parse::<f32>()?;
                        *scopes.last_mut().context("scale outside transform scope")? += 1;
                        surface.push_transform(&Transform::from_row(
                            sx,
                            0.0,
                            0.0,
                            sy,
                            px * (1.0 - sx),
                            py * (1.0 - sy),
                        ));
                    } else if s == "pdf:etrans" {
                        for _ in 0..scopes.pop().context("transform stack underflow")? {
                            surface.pop()?;
                        }
                    } else if let Some(spec) =
                        s.strip_prefix("pdf:image matrix 1.0 0.0 0.0 1.0 0.0 0.0 page ")
                    {
                        let (requested, filename) = spec
                            .split_once(" pagebox cropbox (")
                            .context("unsupported PDF image options")?;
                        let requested = requested
                            .parse::<u16>()
                            .context("invalid PDF page number")?;
                        let name = filename
                            .strip_suffix(')')
                            .context("invalid PDF image filename")?;
                        let index = usize::from(requested.saturating_sub(1));
                        let dir = asset_dir.context("asset directory is required for images")?;
                        let pdf = std::sync::Arc::new(
                            Pdf::new(std::fs::read(asset_path(dir, name)?)?)
                                .map_err(|e| anyhow::anyhow!("PDF image load failed: {e:?}"))?,
                        );
                        let (w, h) = pdf
                            .pages()
                            .get(index)
                            .context("PDF page is out of range")?
                            .render_dimensions();
                        let image = PdfDocument::new(pdf);
                        surface.push_transform(&Transform::from_translate(px, py - h));
                        surface.draw_pdf_page(
                            &image,
                            Size::from_wh(w, h).context("invalid image dimensions")?,
                            index,
                        );
                        surface.pop()?;
                    } else if let Some(spec) = s.strip_prefix("pdf:image bbox ") {
                        let (options, filename) =
                            spec.split_once('(').context("invalid image special")?;
                        let name = filename
                            .trim()
                            .strip_suffix(')')
                            .context("invalid image filename")?;
                        let tokens: Vec<_> = options.split_whitespace().collect();
                        let ["0", "0", right, top, "clip", "0", "width", width] = tokens.as_slice()
                        else {
                            bail!("unsupported raster image options");
                        };
                        let bw = right.parse::<f32>()?;
                        let bh = top.parse::<f32>()?;
                        let w = width
                            .strip_suffix("pt")
                            .context("unsupported image unit")?
                            .parse::<f32>()?
                            * 72.0
                            / 72.27;
                        let h = w * bh / bw;
                        if !w.is_finite() || !h.is_finite() || w <= 0.0 || h <= 0.0 {
                            bail!("invalid image dimensions");
                        }
                        let dir = asset_dir.context("asset directory is required for images")?;
                        let data = std::fs::read(asset_path(dir, name)?)?;
                        let image = if data.starts_with(&[0xff, 0xd8]) {
                            krilla::image::Image::from_jpeg(data.into(), false)
                        } else {
                            krilla::image::Image::from_png(data.into(), false)
                        }
                        .map_err(|e| anyhow::anyhow!("raster image: {e}"))?;
                        // A width-only image special preserves pixel aspect ratio,
                        // even when its TeX box used unequal horizontal/vertical DPI.
                        let (pixel_width, pixel_height) = image.size();
                        let h = w * pixel_height as f32 / pixel_width as f32;
                        surface.push_transform(&Transform::from_translate(px, py - h));
                        surface.draw_image(
                            image,
                            Size::from_wh(w, h).context("invalid raster dimensions")?,
                        );
                        surface.pop()?;
                    } else {
                        bail!("unsupported special: {s}");
                    }
                    continue;
                }
            };
            let (font, size, unicode) = fonts.get(&id).context("undefined font")?;
            if glyphs.is_empty() {
                continue;
            }
            if glyphs.len() != xs.len() || glyphs.len() != ys.len() {
                bail!("inconsistent glyph positions");
            }
            let mut text = String::new();
            let mut positioned = Vec::with_capacity(glyphs.len());
            for (i, gid) in glyphs.iter().enumerate() {
                let value = unicode.get(gid).context("glyph has no Unicode mapping")?;
                let start = text.len();
                text.push_str(value);
                let advance = xs
                    .get(i + 1)
                    .map(|next| bp(*next - xs[i]) / *size)
                    .unwrap_or(0.0);
                positioned.push(KrillaGlyph::new(
                    GlyphId::new(u32::from(*gid)),
                    advance,
                    0.0,
                    bp(ys[0] - ys[i]) / *size,
                    0.0,
                    start..text.len(),
                    None,
                ));
            }
            surface.draw_glyphs(
                Point::from_xy(72.0 + bp(xs[0]), 72.0 + bp(ys[0])),
                &positioned,
                font.clone(),
                &text,
                *size,
                false,
            );
        }
        if !scopes.is_empty() || !pdf_code.balanced() {
            bail!(
                "unbalanced graphics state: transforms {}, colors {}",
                scopes.len(),
                colors.len()
            );
        }
        surface.finish()?;
        page.finish();
    }
    let pdf = doc
        .finish()
        .map_err(|e| anyhow::anyhow!("PDF errors: {e:?}"))?;
    Ok(pdf)
}
