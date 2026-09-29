//! Restore pushed transforms before Surface is dropped on an early error.
use anyhow::{Result, bail};
use krilla::{geom::Transform, surface::Surface};
use std::ops::{Deref, DerefMut};
pub struct SafeSurface<'a> {
    inner: Option<Surface<'a>>,
    depth: usize,
}
impl<'a> SafeSurface<'a> {
    pub fn new(inner: Surface<'a>) -> Self {
        Self {
            inner: Some(inner),
            depth: 0,
        }
    }
    pub fn push_transform(&mut self, matrix: &Transform) {
        self.inner.as_mut().unwrap().push_transform(matrix);
        self.depth += 1;
    }
    pub fn pop(&mut self) -> Result<()> {
        if self.depth == 0 {
            bail!("surface graphics stack underflow");
        }
        self.inner.as_mut().unwrap().pop();
        self.depth -= 1;
        Ok(())
    }
    pub fn finish(mut self) -> Result<()> {
        if self.depth != 0 {
            bail!("unbalanced surface transforms: {}", self.depth);
        }
        self.inner.take().unwrap().finish();
        Ok(())
    }
}
impl<'a> Deref for SafeSurface<'a> {
    type Target = Surface<'a>;
    fn deref(&self) -> &Self::Target {
        self.inner.as_ref().unwrap()
    }
}
impl<'a> DerefMut for SafeSurface<'a> {
    fn deref_mut(&mut self) -> &mut Self::Target {
        self.inner.as_mut().unwrap()
    }
}
impl Drop for SafeSurface<'_> {
    fn drop(&mut self) {
        if let Some(inner) = self.inner.as_mut() {
            while self.depth > 0 {
                inner.pop();
                self.depth -= 1;
            }
        }
    }
}
