


function init_websocket() {
    // Connect to Web Socket
    ws = new WebSocket(WS_URL);

    // Set event handlers.
    ws.onopen = function () {
      console.log("onopen");
    };

    ws.onmessage = function (e) {
      // e.data contains received string.

      console.log("onmessage: " + e.data);
      process_ws_commands(e.data);
    };

    ws.onclose = function () {
      console.log("onclose");
    };

    ws.onerror = function (e) {
      console.log("onerror");
      console.log(e);
    };
}

function process_ws_commands (data) {
  data = JSON.parse(data);
  if (!("command" in data)) {
     console.log("No command in received data")
     return
  }
  switch (data.command) {
    case "update_svg":
      d3.select("#svgViewer").html(data.content);
      console.log("Updating SVG");
      initD3();
      break;
    case "refresh_page":
      window.location.href = window.location.href;
      break;
    case "close":
      ws.close();;
      break;
  }

}