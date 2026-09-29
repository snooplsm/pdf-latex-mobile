//! Isolated offline compiler probe. This accepts Typst, not LaTeX.
use std::{
    collections::HashMap,
    path::{Path, PathBuf},
};
use typst::{
    Library, LibraryExt, World,
    diag::{FileError, FileResult},
    foundations::{Bytes, Datetime, Duration},
    syntax::{FileId, RootedPath, Source, VirtualPath, VirtualRoot},
    text::{Font, FontBook},
    utils::LazyHash,
};

struct OfflineWorld {
    library: LazyHash<Library>,
    book: LazyHash<FontBook>,
    fonts: Vec<Font>,
    source: Source,
    files: HashMap<FileId, Bytes>,
}
impl World for OfflineWorld {
    fn library(&self) -> &LazyHash<Library> {
        &self.library
    }
    fn book(&self) -> &LazyHash<FontBook> {
        &self.book
    }
    fn main(&self) -> FileId {
        self.source.id()
    }
    fn source(&self, id: FileId) -> FileResult<Source> {
        if id == self.main() {
            Ok(self.source.clone())
        } else {
            Err(FileError::NotFound(PathBuf::from(
                "imports disabled in probe",
            )))
        }
    }
    fn file(&self, id: FileId) -> FileResult<Bytes> {
        self.files
            .get(&id)
            .cloned()
            .ok_or_else(|| FileError::NotFound(PathBuf::from("asset not supplied")))
    }
    fn font(&self, index: usize) -> Option<Font> {
        self.fonts.get(index).cloned()
    }
    fn today(&self, _: Option<Duration>) -> Option<Datetime> {
        Datetime::from_ymd(2026, 9, 29)
    }
}

pub fn compile(
    source: &str,
    fonts: &[PathBuf],
    assets: &[(String, PathBuf)],
) -> Result<Vec<u8>, String> {
    let fonts: Vec<Font> = fonts
        .iter()
        .map(|p| std::fs::read(p).map(Bytes::new).map_err(|e| e.to_string()))
        .collect::<Result<Vec<_>, _>>()?
        .into_iter()
        .flat_map(Font::iter)
        .collect();
    let main = FileId::new(RootedPath::new(
        VirtualRoot::Project,
        VirtualPath::new("main.typ").unwrap(),
    ));
    let mut files = HashMap::new();
    files.insert(main, Bytes::new(source.as_bytes().to_vec()));
    for (name, path) in assets {
        files.insert(
            FileId::new(RootedPath::new(
                VirtualRoot::Project,
                VirtualPath::new(name).map_err(|e| e.to_string())?,
            )),
            Bytes::new(std::fs::read(path).map_err(|e| e.to_string())?),
        );
    }
    let world = OfflineWorld {
        library: LazyHash::new(Library::default()),
        book: LazyHash::new(FontBook::from_fonts(&fonts)),
        fonts,
        source: Source::new(main, source.to_owned()),
        files,
    };
    let document = typst::compile::<typst_layout::PagedDocument>(&world)
        .output
        .map_err(|e| format!("{e:?}"))?;
    typst_pdf::pdf(&document, &typst_pdf::PdfOptions::default()).map_err(|e| format!("{e:?}"))
}

/// Probe-only C entry point: paths point to NUL-terminated UTF-8 strings.
/// Returns 0 on success and 1 on failure. Do not expose as a production API.
/// # Safety
/// All pointers must be valid NUL-terminated strings for this call.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn typst_probe_compile(
    source: *const std::ffi::c_char,
    font: *const std::ffi::c_char,
    output: *const std::ffi::c_char,
) -> i32 {
    std::panic::catch_unwind(|| {
        let source = unsafe { std::ffi::CStr::from_ptr(source) }
            .to_str()
            .map_err(|_| ())?;
        let font = unsafe { std::ffi::CStr::from_ptr(font) }
            .to_str()
            .map_err(|_| ())?;
        let output = unsafe { std::ffi::CStr::from_ptr(output) }
            .to_str()
            .map_err(|_| ())?;
        let pdf = compile(source, &[Path::new(font).to_owned()], &[]).map_err(|_| ())?;
        std::fs::write(output, pdf).map_err(|_| ())
    })
    .ok()
    .and_then(Result::ok)
    .map_or(1, |_| 0)
}
