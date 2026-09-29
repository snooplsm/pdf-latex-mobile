// MIT: experimental replacement for XeTeX image metadata queries.
use std::{io::Cursor, panic::{catch_unwind, AssertUnwindSafe}};
use hayro_syntax::{Pdf, page::Rotation};

unsafe fn bytes<'a>(data: *const u8, len: usize) -> Option<&'a [u8]> {
    if data.is_null() || len == 0 || len > 256 * 1024 * 1024 { return None; }
    Some(unsafe { std::slice::from_raw_parts(data, len) })
}

#[no_mangle]
pub unsafe extern "C" fn lm_probe_pdf_count(data: *const u8, len: usize) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        let raw=unsafe {bytes(data,len)}?;
        let pdf=Pdf::new(raw.to_vec()).ok()?;
        i32::try_from(pdf.pages().len()).ok()
    })).ok().flatten().unwrap_or(-1)
}

#[no_mangle]
pub unsafe extern "C" fn lm_probe_pdf_box(data: *const u8, len: usize, requested: i32, box_type: i32, output: *mut f64) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        if output.is_null() {return None;}
        let pdf=Pdf::new(unsafe {bytes(data,len)}?.to_vec()).ok()?;
        let count=i32::try_from(pdf.pages().len()).ok()?;
        if count==0 {return None;}
        let index=if requested<0 {count+requested} else {requested.saturating_sub(1)}.clamp(0,count-1);
        let page=&pdf.pages()[index as usize];
        // Rotation support must be verified before accepting rotated input.
        if !matches!(page.rotation(),Rotation::None) {return None;}
        let bounds=match box_type {
            1|6 => page.crop_box(),
            2 => page.media_box(),
            _ => return None,
        };
        let values=[bounds.x0,bounds.y0,bounds.width(),bounds.height()];
        if !values.iter().all(|v|v.is_finite()) || values[2]<=0.0 || values[3]<=0.0 {return None;}
        unsafe {std::ptr::copy_nonoverlapping(values.as_ptr(),output,4)};
        Some(0)
    })).ok().flatten().unwrap_or(-1)
}


fn jpeg_size(raw: &[u8]) -> Option<[f64; 2]> {
    let mut decoder = zune_jpeg::JpegDecoder::new(Cursor::new(raw));
    decoder.decode_headers().ok()?;
    let info = decoder.info()?;
    let mut dpi = [72.0, 72.0];
    let mut pos = 2usize;
    while pos < raw.len() {
        if *raw.get(pos)? != 0xff { return None; }
        while *raw.get(pos)? == 0xff { pos += 1; }
        let marker = *raw.get(pos)?; pos += 1;
        if matches!(marker, 0xda | 0xd9) { break; }
        if matches!(marker, 0x01 | 0xd0..=0xd7) { continue; }
        let length = usize::from(u16::from_be_bytes(raw.get(pos..pos+2)?.try_into().ok()?));
        if length < 2 { return None; }
        let segment = raw.get(pos+2..pos.checked_add(length)?)?;
        if marker == 0xe0 && segment.starts_with(b"JFIF\0") {
            if segment.len() < 14 { return None; }
            let scale = match segment[7] { 0 => 0.0, 1 => 1.0, 2 => 2.54, _ => return None };
            if scale != 0.0 {
                dpi = [f64::from(u16::from_be_bytes([segment[8],segment[9]]))*scale,
                       f64::from(u16::from_be_bytes([segment[10],segment[11]]))*scale];
                if dpi.iter().any(|v| *v == 0.0) { return None; }
            }
        }
        pos += length;
    }
    Some([f64::from(info.width)/dpi[0], f64::from(info.height)/dpi[1]])
}

#[no_mangle]
pub unsafe extern "C" fn lm_probe_raster_size(data: *const u8, len: usize, output: *mut f64) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        if output.is_null() {return None;}
        let raw=unsafe {bytes(data,len)}?;
        if raw.starts_with(&[0xff, 0xd8]) {
            let values = jpeg_size(raw)?;
            if values.iter().any(|v| !v.is_finite() || *v <= 0.0) { return None; }
            unsafe {std::ptr::copy_nonoverlapping(values.as_ptr(),output,2)};
            return Some(0);
        }
        let decoder=png::Decoder::new(Cursor::new(raw));
        let reader=decoder.read_info().ok()?;
        let info=reader.info();
        let (xdpi,ydpi)=match info.pixel_dims {
            Some(dim) if dim.unit==png::Unit::Meter && dim.xppu>0 && dim.yppu>0 => (f64::from(dim.xppu)*0.0254,f64::from(dim.yppu)*0.0254),
            _ => (72.0,72.0),
        };
        let values=[f64::from(info.width)/xdpi,f64::from(info.height)/ydpi];
        if values.iter().any(|v|!v.is_finite() || *v<=0.0) {return None;}
        unsafe {std::ptr::copy_nonoverlapping(values.as_ptr(),output,2)};
        Some(0)
    })).ok().flatten().unwrap_or(-1)
}
