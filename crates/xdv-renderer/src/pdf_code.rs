use crate::safe_surface::SafeSurface as Surface;
// A deliberately strict PDF path-operator interpreter for XDV drawing specials.
use anyhow::{Context, Result, bail};
use krilla::{
    color::{Color, cmyk, rgb},
    geom::{PathBuilder, Transform},
    paint::{Fill, LineCap, LineJoin, Stroke, StrokeDash},
};

#[derive(Clone)]
struct State {
    fill: Fill,
    stroke: Stroke,
    transforms: usize,
}
struct Saved {
    state: State,
}
pub struct PdfCode {
    state: State,
    stack: Vec<Saved>,
    origin: (f32, f32),
    origins: Vec<(f32, f32)>,
    path: Option<PathBuilder>,
}
impl Default for PdfCode {
    fn default() -> Self {
        Self {
            state: State {
                fill: Fill::default(),
                stroke: Stroke::default(),
                transforms: 0,
            },
            stack: vec![],
            origin: (0.0, 0.0),
            origins: vec![],
            path: None,
        }
    }
}
impl PdfCode {
    pub fn balanced(&self) -> bool {
        self.stack.is_empty()
            && self.origins.is_empty()
            && self.path.is_none()
            && self.state.transforms == 0
    }
    pub fn begin(&mut self, x: f32, y: f32) {
        self.origins.push(self.origin);
        self.origin = (x, y);
    }
    fn save(&mut self) {
        self.stack.push(Saved {
            state: self.state.clone(),
        });
        self.state.transforms = 0;
    }
    pub fn end(&mut self, surface: &mut Surface<'_>) -> Result<()> {
        let _ = surface;
        self.origin = self.origins.pop().context("content stack underflow")?;
        Ok(())
    }
    fn restore(&mut self, surface: &mut Surface<'_>) -> Result<()> {
        let saved = self.stack.pop().context("PDF graphics stack underflow")?;
        for _ in 0..self.state.transforms {
            surface.pop()?;
        }
        self.state = saved.state;
        surface.set_fill(Some(self.state.fill.clone()));
        Ok(())
    }
    fn point(&self, x: f32, y: f32) -> (f32, f32) {
        (self.origin.0 + x, self.origin.1 - y)
    }
    fn draw(&mut self, surface: &mut Surface<'_>, fill: bool, stroke: bool) -> Result<()> {
        if let Some(builder) = self.path.take() {
            if let Some(path) = builder.finish() {
                surface.set_fill(if fill {
                    Some(self.state.fill.clone())
                } else {
                    None
                });
                surface.set_stroke(if stroke {
                    Some(self.state.stroke.clone())
                } else {
                    None
                });
                surface.draw_path(&path);
                surface.set_stroke(None);
                surface.set_fill(Some(self.state.fill.clone()));
            }
        }
        Ok(())
    }
    pub fn invoke(&mut self, surface: &mut Surface<'_>, code: &str) -> Result<()> {
        let spaced = code.replace('[', " [ ").replace(']', " ] ");
        let mut values = vec![];
        let mut array_start = None;
        let mut array = None;
        for token in spaced.split_whitespace() {
            if let Ok(number) = token.parse::<f32>() {
                if !number.is_finite() {
                    bail!("nonfinite PDF operand");
                }
                values.push(number);
                continue;
            }
            if token == "[" {
                if array_start.is_some() || array.is_some() {
                    bail!("nested/repeated array");
                }
                array_start = Some(values.len());
                continue;
            }
            if token == "]" {
                let start = array_start.take().context("unexpected closing bracket")?;
                array = Some(values.drain(start..).collect::<Vec<_>>());
                continue;
            }
            if array_start.is_some() {
                bail!("operator in numeric array");
            }
            let operands = std::mem::take(&mut values);
            let n = |count| -> Result<()> {
                if operands.len() != count {
                    bail!("{token}: expected {count} operands, got {}", operands.len());
                }
                Ok(())
            };
            match token {
                "q" => {
                    n(0)?;
                    self.save();
                }
                "Q" => {
                    n(0)?;
                    self.restore(surface)?;
                }
                "cm" => {
                    n(6)?;
                    if self.path.is_some() {
                        bail!("matrix change during an unfinished path");
                    }
                    let [a, b, c, d, e, f]: [f32; 6] = operands.try_into().unwrap();
                    let (x, y) = self.origin;
                    surface.push_transform(&Transform::from_row(
                        a,
                        -b,
                        -c,
                        d,
                        x - a * x + c * y + e,
                        y + b * x - d * y - f,
                    ));
                    self.state.transforms += 1;
                }
                "w" => {
                    n(1)?;
                    if operands[0] <= 0.0 {
                        bail!("hairline/negative stroke unsupported");
                    }
                    self.state.stroke.width = operands[0];
                }
                "M" => {
                    n(1)?;
                    if operands[0] < 1.0 {
                        bail!("invalid miter limit");
                    }
                    self.state.stroke.miter_limit = operands[0];
                }
                "J" => {
                    n(1)?;
                    self.state.stroke.line_cap = match operands[0] {
                        0.0 => LineCap::Butt,
                        1.0 => LineCap::Round,
                        2.0 => LineCap::Square,
                        _ => bail!("invalid line cap"),
                    };
                }
                "j" => {
                    n(1)?;
                    self.state.stroke.line_join = match operands[0] {
                        0.0 => LineJoin::Miter,
                        1.0 => LineJoin::Round,
                        2.0 => LineJoin::Bevel,
                        _ => bail!("invalid line join"),
                    };
                }
                "d" => {
                    n(1)?;
                    let dash = array.take().context("dash array missing")?;
                    if dash.iter().any(|v| *v < 0.0) {
                        bail!("negative dash");
                    }
                    self.state.stroke.dash = if dash.is_empty() {
                        None
                    } else {
                        Some(StrokeDash {
                            array: dash,
                            offset: operands[0],
                        })
                    };
                }
                "g" | "G" | "rg" | "RG" | "k" | "K" => {
                    n(match token {
                        "k" | "K" => 4,
                        "g" | "G" => 1,
                        _ => 3,
                    })?;
                    if operands.iter().any(|v| !(0.0..=1.0).contains(v)) {
                        bail!("invalid PDF color");
                    }
                    let c: Color = if operands.len() == 1 {
                        let v = operands[0];
                        rgb::Color::new_normalized(v, v, v)
                            .context("invalid gray")?
                            .into()
                    } else if operands.len() == 4 {
                        cmyk::Color::new_normalized(
                            operands[0],
                            operands[1],
                            operands[2],
                            operands[3],
                        )
                        .context("invalid CMYK")?
                        .into()
                    } else {
                        rgb::Color::new_normalized(operands[0], operands[1], operands[2])
                            .context("invalid RGB")?
                            .into()
                    };
                    if token.chars().next().unwrap().is_uppercase() {
                        self.state.stroke.paint = c.into();
                    } else {
                        self.state.fill.paint = c.into();
                        surface.set_fill(Some(self.state.fill.clone()));
                    }
                }
                "m" | "l" => {
                    n(2)?;
                    let (x, y) = self.point(operands[0], operands[1]);
                    if token == "m" {
                        self.path.get_or_insert_with(PathBuilder::new).move_to(x, y);
                    } else {
                        self.path
                            .as_mut()
                            .context("line without path")?
                            .line_to(x, y);
                    }
                }
                "c" => {
                    n(6)?;
                    let (a, b) = self.point(operands[0], operands[1]);
                    let (c, d) = self.point(operands[2], operands[3]);
                    let (e, f) = self.point(operands[4], operands[5]);
                    self.path
                        .as_mut()
                        .context("curve without path")?
                        .cubic_to(a, b, c, d, e, f);
                }
                "re" => {
                    n(4)?;
                    let x = operands[0];
                    let y = operands[1];
                    let w = operands[2];
                    let h = operands[3];
                    let points = [
                        self.point(x, y),
                        self.point(x + w, y),
                        self.point(x + w, y + h),
                        self.point(x, y + h),
                    ];
                    let p = self.path.get_or_insert_with(PathBuilder::new);
                    p.move_to(points[0].0, points[0].1);
                    for (x, y) in &points[1..] {
                        p.line_to(*x, *y);
                    }
                    p.close();
                }
                "h" => {
                    n(0)?;
                    self.path.as_mut().context("close without path")?.close();
                }
                "n" => {
                    n(0)?;
                    self.path = None;
                }
                "S" | "f" | "F" | "B" => {
                    n(0)?;
                    self.draw(surface, token != "S", token == "S" || token == "B")?;
                }
                _ => bail!("unsupported PDF drawing operator {token}"),
            }
            if array.is_some() {
                bail!("unused array operand");
            }
        }
        if !values.is_empty() || array.is_some() || array_start.is_some() {
            bail!("unfinished PDF operands");
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use krilla::Document;

    #[test]
    fn error_after_transform_does_not_panic_on_cleanup() {
        let mut document = Document::new();
        let mut page = document.start_page();
        {
            let mut surface = Surface::new(page.surface());
            let mut code = PdfCode::default();
            let error = code
                .invoke(&mut surface, "q 2 0 0 2 0 0 cm /Unknown sh")
                .unwrap_err();
            assert!(
                error
                    .to_string()
                    .contains("unsupported PDF drawing operator")
            );
        }
        page.finish();
        assert!(document.finish().is_ok());
    }

    #[test]
    fn relative_content_can_end_inside_saved_graphics_state() {
        let mut document = Document::new();
        let mut page = document.start_page();
        let mut surface = Surface::new(page.surface());
        let mut code = PdfCode::default();
        code.begin(100.0, 100.0);
        code.invoke(&mut surface, "q -1 0 0 -1 0 0 cm q").unwrap();
        code.end(&mut surface).unwrap();
        code.begin(120.0, 90.0);
        code.invoke(&mut surface, "0 0 m 10 10 l S Q Q").unwrap();
        code.end(&mut surface).unwrap();
        assert!(code.balanced());
        surface.finish().unwrap();
        page.finish();
        assert!(document.finish().is_ok());
    }

    #[test]
    fn malformed_operator_and_stack_underflow_are_errors() {
        let mut document = Document::new();
        let mut page = document.start_page();
        let mut surface = Surface::new(page.surface());
        assert!(PdfCode::default().invoke(&mut surface, "Q").is_err());
        assert!(PdfCode::default().invoke(&mut surface, "10 m").is_err());
        assert!(
            PdfCode::default()
                .invoke(&mut surface, "[1 -2] 0 d")
                .is_err()
        );
        for invalid in ["0 0 0 k", "0 0 0 1.01 K", "0 -0.1 0 0 k", "0 0 0 NaN K"] {
            assert!(PdfCode::default().invoke(&mut surface, invalid).is_err());
        }
        surface.finish().unwrap();
        page.finish();
    }
}
