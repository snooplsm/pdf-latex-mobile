//! Traditional TeX character widths; all positions remain integer DVI units.
use anyhow::{Result, bail, ensure};

pub struct Metrics {
    widths: [Option<i32>; 256],
}
impl Metrics {
    pub fn parse(data: &[u8], size: u32) -> Result<Self> {
        ensure!(
            data.len() >= 24 && data.len() % 4 == 0,
            "truncated TFM header"
        );
        let word = |i: usize| u16::from_be_bytes([data[2 * i], data[2 * i + 1]]) as usize;
        let lf = word(0);
        let lh = word(1);
        let bc = word(2);
        let ec = word(3);
        let nw = word(4);
        ensure!(
            lf * 4 == data.len() && lh >= 2 && ec < 256 && bc <= ec + 1 && nw > 0,
            "invalid TFM dimensions"
        );
        let nc = ec + 1 - bc;
        ensure!(
            lf == 6 + lh + nc + (4..12).map(word).sum::<usize>(),
            "inconsistent TFM length"
        );
        ensure!(size > 0 && size < (1 << 27), "unsupported TFM scale");
        let table = 4 * (6 + lh + nc);
        ensure!(
            data[table..table + 4] == [0; 4],
            "nonzero TFM missing-glyph width"
        );
        let mut widths = [None; 256];
        for c in bc..=ec {
            let index = data[4 * (6 + lh + c - bc)] as usize;
            ensure!(index < nw, "TFM width index out of bounds");
            if index == 0 {
                continue;
            }
            let offset = table + 4 * index;
            let fixed = i32::from_be_bytes(data[offset..offset + 4].try_into().unwrap());
            let scaled = (i64::from(fixed) * i64::from(size)) >> 20;
            widths[c] = Some(i32::try_from(scaled)?);
        }
        Ok(Self { widths })
    }
    pub fn width(&self, character: i32) -> Result<i32> {
        if !(0..256).contains(&character) {
            bail!("TFM character outside 8-bit encoding");
        }
        self.widths[character as usize]
            .ok_or_else(|| anyhow::anyhow!("missing TFM character {character}"))
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Vec<u8> {
        let mut b = vec![];
        for v in [11u16, 2, 65, 65, 2, 0, 0, 0, 0, 0, 0, 0] {
            b.extend(v.to_be_bytes());
        }
        b.extend([0; 8]);
        b.extend([1, 0, 0, 0]);
        b.extend([0; 4]);
        b.extend(0x00080000i32.to_be_bytes());
        b
    }
    #[test]
    fn width_and_missing_character() {
        let m = Metrics::parse(&fixture(), 655360).unwrap();
        assert_eq!(m.width(65).unwrap(), 327680);
        assert!(m.width(66).is_err());
        assert!(m.width(256).is_err());
    }
    #[test]
    fn malformed_tables_fail() {
        let b = fixture();
        assert!(Metrics::parse(&b[..b.len() - 1], 655360).is_err());
        let mut b = fixture();
        b[32] = 3;
        assert!(Metrics::parse(&b, 655360).is_err());
        let mut b = fixture();
        b[1] = 12;
        assert!(Metrics::parse(&b, 655360).is_err());
    }
}
