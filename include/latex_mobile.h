#ifndef LATEX_MOBILE_H
#define LATEX_MOBILE_H
#ifdef __cplusplus
extern "C" {
#endif
/* Blocking. Pass UTF-8 JSON; release the returned UTF-8 JSON with lm_string_free.
   Compiles are serialized. Only compile trusted LaTeX: this is not a sandbox. */
char *lm_compile(const char *request);
void lm_string_free(char *value);
#ifdef __cplusplus
}
#endif
#endif
