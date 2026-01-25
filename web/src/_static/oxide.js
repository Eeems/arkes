/*global Sentry, ackeeTracker*/
var dnt =
    (window.doNotTrack && window.doNotTrack === "1") ||
    (navigator.doNotTrack && (navigator.doNotTrack === "yes" || navigator.doNotTrack === "1" )) ||
    (navigator.msDoNotTrack && navigator.msDoNotTrack === "1") ||
    ("msTrackingProtectionEnabled" in window.external && window.external.msTrackingProtectionEnabled());
if(typeof ackeeTracker !== "undefined"){
    ackeeTracker
        .create("https://peek.eeems.website", { detailed: !dnt })
        .record("9f083ee0-617c-46fa-bf5d-7385e0d590d5");
}else{
    console.error("ackeeTracker is missing");
}
function setup(){
    document
        .querySelectorAll('img.screenshot')
        .forEach(function(img){
            img.addEventListener('click', function(){
                if(document.fullscreenEnabled){
                    if(!document.fullscreenElement){
                        img
                        .requestFullscreen({ navigationUI: "show" })
                        .catch(e => console.error(e));
                    }else{
                        document
                            .exitFullscreen()
                            .catch(e => console.error(e));
                    }
                }else{
                    let el = document.createElement("img");
                    el.src = img.src;
                    el.title = "Click to close image";
                    el.classList.add("fullscreen");
                    el.addEventListener('click', () => document.body.removeChild(el));
                    el.addEventListener('keydown', function(e){
                        if(e.key == "Escape" || e.key == "F11"){
                            document.body.removeChild(el);
                        }
                    });
                    document.body.appendChild(el);
                }
            });
        });
}
if(document.readyState == "loading"){
    window.addEventListener('DOMContentLoaded', setup);
}else{
    setup();
}
