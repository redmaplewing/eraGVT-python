// 入力後に最下部へスクロール（Emuera のコンソールと同じ見え方）
window.addEventListener("load", () => {
  window.scrollTo(0, document.body.scrollHeight);
  document.getElementById("value")?.focus();
});
