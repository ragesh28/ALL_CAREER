/* Visual-only UI hygiene shared by every extension surface.
 * It removes legacy pictographs from rendered labels without changing commands,
 * IDs, storage, or application state. */
(() => {
  const pictographs = /[\p{Extended_Pictographic}\uFE0F\u200D]/gu;
  const clean = (node) => {
    if (node.nodeType !== Node.TEXT_NODE) return;
    const cleaned = node.nodeValue.replace(pictographs, '').replace(/ {2,}/g, ' ');
    if (cleaned !== node.nodeValue) node.nodeValue = cleaned;
  };
  const cleanTree = (root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) clean(walker.currentNode);
  };
  const start = () => {
    cleanTree(document.body);
    new MutationObserver((records) => records.forEach((record) => {
      record.addedNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE) clean(node);
        else if (node.nodeType === Node.ELEMENT_NODE) cleanTree(node);
      });
      if (record.type === 'characterData') clean(record.target);
    })).observe(document.body, { childList: true, subtree: true, characterData: true });
  };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', start) : start();
})();
