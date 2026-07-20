import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outputDir = path.resolve(root, process.argv[2] || '_deploy');
const deployVersion = process.argv[3] || 'local-build';

if (outputDir === root || !outputDir.startsWith(`${root}${path.sep}`)) {
    throw new Error('Deployment output must be a child directory of the project root.');
}

const read = relativePath => fs.readFile(path.join(root, relativePath), 'utf8');
const escapeInlineScript = source => source
    .replace(/<\/script/gi, '<\\/script')
    .replace(/<!--/g, '<\\!--')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');

const [sourceHtml, vueSource, bookmarksSource] = await Promise.all([
    read('index.html'),
    read('assets/vue.global.prod.js'),
    read('data/bookmarks.json'),
]);

const bookmarks = JSON.parse(bookmarksSource);
const inlineVue = `<script data-deploy-inline="vue">${escapeInlineScript(vueSource)}</script>`;
const inlineBookmarks = `<script data-deploy-inline="bookmarks">globalThis.__NEUFAN_BOOKMARKS__=${escapeInlineScript(JSON.stringify(bookmarks))};</script>`;

let deployedHtml = sourceHtml
    .replace(
        /\s*<!-- DEPLOY:VUE:START -->[\s\S]*?<!-- DEPLOY:VUE:END -->/,
        () => `\n    ${inlineVue}`,
    )
    .replace('<!-- DEPLOY:BOOKMARKS -->', () => inlineBookmarks)
    .replaceAll('__DEPLOY_VERSION__', deployVersion);

const buildChecks = {
    inlineVue: deployedHtml.includes('data-deploy-inline="vue"'),
    inlineBookmarks: deployedHtml.includes('data-deploy-inline="bookmarks"'),
    removedVueMarker: !deployedHtml.includes('DEPLOY:VUE'),
    removedBookmarksMarker: !deployedHtml.includes('DEPLOY:BOOKMARKS'),
};
if (Object.values(buildChecks).includes(false)) {
    throw new Error(`Failed to inline deployment assets: ${JSON.stringify(buildChecks)}`);
}

await fs.rm(outputDir, { recursive: true, force: true });
await fs.mkdir(path.join(outputDir, 'data'), { recursive: true });
await fs.mkdir(path.join(outputDir, 'assets'), { recursive: true });

await Promise.all([
    fs.writeFile(path.join(outputDir, 'index.html'), deployedHtml, 'utf8'),
    ...['about.html', 'editor.html', 'icon.jpg'].map(file =>
        fs.copyFile(path.join(root, file), path.join(outputDir, file))),
    fs.copyFile(path.join(root, 'data', 'bookmarks.json'), path.join(outputDir, 'data', 'bookmarks.json')),
    fs.copyFile(path.join(root, 'assets', 'vue.global.prod.js'), path.join(outputDir, 'assets', 'vue.global.prod.js')),
]);

console.log(JSON.stringify({
    output: path.relative(root, outputDir),
    version: deployVersion,
    htmlBytes: Buffer.byteLength(deployedHtml),
    bookmarkPages: Object.keys(bookmarks).length,
}));
