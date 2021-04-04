// copied from:
// https://stackoverflow.com/a/15369753/4046512
document.onpaste = function (event) {
  var items = event.clipboardData.items;

  var blob = null;
  for (var i = 0; i < items.length; i++) {
    if (items[i].type.indexOf("image") === 0) {
      blob = items[i].getAsFile();
    }
  }

  if (blob == null)
    return;

  var reader = new FileReader();
  reader.onload = function(event) {
    var img = document.createElement("img");
    img.src = event.target.result;
    console.log(img);
    var navigation = document.getElementsByClassName("navigation")[0];
    navigation.parentElement.insertBefore(img, navigation);
  };
  reader.readAsDataURL(blob);
}
