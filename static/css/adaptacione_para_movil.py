window.onclick = function(event){
    document.querySelectorAll('.modal').forEach(m=>{
        if(event.target==m){ m.style.display='none'; }
    });
}
