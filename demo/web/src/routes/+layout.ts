// Fully static site: prerender every route to HTML, with directory-style URLs so it
// serves cleanly from GitHub Pages (each route -> its own index.html).
export const prerender = true;
export const trailingSlash = 'always';
