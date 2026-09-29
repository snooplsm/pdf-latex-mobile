/* MIT: independent metadata bridge for the experimental mobile engine. */
extern int lm_probe_pdf_count(const unsigned char *, size_t);
extern int lm_probe_pdf_box(const unsigned char *, size_t, int, int, double *);
extern int lm_probe_raster_size(const unsigned char *, size_t, double *);

static unsigned char *picture_bytes(rust_input_handle_t handle, size_t *length) {
    *length = ttstub_input_get_size(handle);
    if (*length == 0 || *length > 256u * 1024u * 1024u) return NULL;
    unsigned char *data = malloc(*length);
    if (data == NULL) return NULL;
    ttstub_input_seek(handle, 0, SEEK_SET);
    if (ttstub_input_read(handle, (char *)data, *length) != (ssize_t)*length) {
        free(data);
        return NULL;
    }
    return data;
}

int count_pdf_file_pages(void) {
    rust_input_handle_t handle = ttstub_input_open(name_of_file, TTBC_FILE_FORMAT_PICT, 0);
    if (handle == INVALID_HANDLE) return 0;
    size_t length;
    unsigned char *data = picture_bytes(handle, &length);
    int count = data == NULL ? 0 : lm_probe_pdf_count(data, length);
    free(data);
    ttstub_input_close(handle);
    return count < 0 ? 0 : count;
}

static int pdf_get_rect(char *filename, rust_input_handle_t handle, int page, int box_type, real_rect *box) {
    (void)filename;
    size_t length;
    unsigned char *data = picture_bytes(handle, &length);
    if (data == NULL) return -1;
    double bounds[4];
    int result = lm_probe_pdf_box(data, length, page, box_type, bounds);
    free(data);
    if (result != 0) return result;
    box->x = bounds[0] * 72.27 / 72.0;
    box->y = bounds[1] * 72.27 / 72.0;
    box->wd = bounds[2] * 72.27 / 72.0;
    box->ht = bounds[3] * 72.27 / 72.0;
    return 0;
}

static int get_image_size_in_inches(rust_input_handle_t handle, double *width, double *height) {
    size_t length;
    unsigned char *data = picture_bytes(handle, &length);
    if (data == NULL) return -1;
    double size[2];
    int result = lm_probe_raster_size(data, length, size);
    free(data);
    if (result != 0) return result;
    *width = size[0];
    *height = size[1];
    return 0;
}
