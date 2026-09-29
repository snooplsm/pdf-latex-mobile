"""Preserve normalized CMYK components, avoiding 8-bit color quantization."""
def patch(body):
    start=body.index('pub mod cmyk {');end=body.index('pub mod rgb {',start)
    section=body[start:end]
    old='pub struct Color(pub(crate) u8, pub(crate) u8, pub(crate) u8, pub(crate) u8);'
    assert section.count(old)==1
    section=section.replace(old,'pub struct Color(u32, u32, u32, u32);')
    section=section.replace('Color(cyan, magenta, yellow, black)','Self::new_normalized(cyan as f32 / 255.0, magenta as f32 / 255.0, yellow as f32 / 255.0, black as f32 / 255.0).unwrap()')
    needle='        pub(crate) fn to_pdf_color(self) -> [f32; 4] {'
    assert section.count(needle)==1
    section=section.replace(needle,'''        /// Construct a finite normalized CMYK color without 8-bit quantization.
        pub fn new_normalized(cyan: f32, magenta: f32, yellow: f32, black: f32) -> Option<Self> {
            let bits = |v: f32| if v.is_finite() && (0.0..=1.0).contains(&v) {
                Some(if v == 0.0 { 0.0f32.to_bits() } else { v.to_bits() })
            } else { None };
            Some(Color(bits(cyan)?, bits(magenta)?, bits(yellow)?, bits(black)?))
        }

'''+needle)
    for i in range(4):section=section.replace(f'self.{i} as f32 / 255.0',f'f32::from_bits(self.{i})')
    return body[:start]+section+body[end:]
