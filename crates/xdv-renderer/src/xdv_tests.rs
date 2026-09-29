use anyhow::Result;
use tectonic_xdv::{XdvEvents, XdvParser};
#[derive(Default)]
struct Events {
    fonts: Vec<(i32, String, u32)>,
    chars: Vec<(i32, i32, i32, i32)>,
}
impl XdvEvents for Events {
    type Error = anyhow::Error;
    fn handle_define_font(
        &mut self,
        n: i32,
        _: u32,
        size: u32,
        _: u32,
        _: &str,
        name: &str,
    ) -> Result<()> {
        self.fonts.push((n, name.into(), size));
        Ok(())
    }
    fn handle_character(&mut self, f: i32, c: i32, x: i32, y: i32) -> Result<i32> {
        self.chars.push((f, c, x, y));
        Ok(10)
    }
}
fn fixture() -> Vec<u8> {
    let mut b = vec![247, 7];
    for n in [25_400_000u32, 473_628_672, 1000] {
        b.extend(n.to_be_bytes());
    }
    b.push(0);
    b.extend([243, 1]);
    for n in [0u32, 655360, 655360] {
        b.extend(n.to_be_bytes());
    }
    b.extend([0, 3]);
    b.extend(b"cmr");
    let bop = b.len() as u32;
    b.push(139);
    b.extend([0; 40]);
    b.extend(u32::MAX.to_be_bytes());
    // Set A, push, move right 5/down 7, set B, pop, then set C.
    b.extend([172, 65, 141, 143, 5, 157, 7, 66, 142, 67, 140]);
    let post = b.len() as u32;
    b.push(248);
    for n in [bop, 25_400_000, 473_628_672, 1000, 100, 100] {
        b.extend(n.to_be_bytes());
    }
    b.extend([0, 1, 0, 1]);
    b.push(249);
    b.extend(post.to_be_bytes());
    b.extend([7, 223, 223, 223, 223]);
    b
}
#[test]
fn font_definitions_and_character_advances_survive_stack_operations() {
    let (e, _) = XdvParser::process(&fixture()[..], Events::default()).unwrap();
    assert_eq!(e.fonts, vec![(1, "cmr".into(), 655360)]);
    assert_eq!(e.chars, vec![(1, 65, 0, 0), (1, 66, 15, 7), (1, 67, 10, 0)]);
}
#[test]
fn invalid_font_name_returns_error_instead_of_panicking() {
    let mut b = fixture();
    b[31] = 0xff;
    assert!(XdvParser::process(&b[..], Events::default()).is_err());
}

#[test]
fn page_surface_preserves_precision_and_rejects_nonfinite() {
    let mut input = super::Input::default();
    input.handle_begin_page(&[], -1).unwrap();
    input
        .handle_special(0, 0, b"pdf:pagesize width 421.10078pt height 597.50787pt")
        .unwrap();
    assert!((input.pages[0].width - 419.52755).abs() < 0.0001);
    assert!((input.pages[0].height - 595.2756).abs() < 0.0001);
    assert!(
        input
            .handle_special(0, 0, b"pdf:pagesize width NaNpt height 10pt")
            .is_err()
    );
}

#[test]
fn normalized_rgb_preserves_fractional_components() {
    use krilla::color::rgb::Color;
    assert_ne!(
        Color::new_normalized(0.1, 0.3, 0.7).unwrap(),
        Color::new(26, 77, 179)
    );
    assert_eq!(Color::new_normalized(-0.0, 0.0, 0.0), Some(Color::black()));
    for invalid in [f32::NAN, f32::INFINITY, -0.01, 1.01] {
        assert!(Color::new_normalized(invalid, 0.0, 0.0).is_none());
    }
}

#[test]
fn nested_assets_stay_inside_the_asset_root() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let resolved = super::asset_path(root, "src/lib.rs").unwrap();
    assert_eq!(resolved, root.join("src/lib.rs").canonicalize().unwrap());
    for name in [
        "../Cargo.toml",
        "/etc/passwd",
        "src//lib.rs",
        "src/./lib.rs",
        "C:\\logo.pdf",
        "",
    ] {
        assert!(super::asset_path(root, name).is_err(), "accepted {name}");
    }
}

#[test]
fn color_components_reject_nonfinite_out_of_range_and_wrong_arity() {
    for values in [
        vec!["NaN"],
        vec!["inf", "0", "0"],
        vec!["0", "0", "0", "1.01"],
        vec!["-0.1"],
        vec!["0", "0"],
        vec![],
    ] {
        assert!(super::parse_color_components(&values).is_err());
    }
}
