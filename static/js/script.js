 document.addEventListener('mousemove', (e) => {
            const x = (e.clientX / window.innerWidth) * 10 - 5;
            const y = (e.clientY / window.innerHeight) * 10 - 5;
            document.body.style.backgroundPosition = `${50 + x}% ${50 + y}%`;
        });
function toggleExpand(id, btn) {
    const content = document.getElementById('content-' + id);
    content.classList.toggle('expanded');
    
    if (content.classList.contains('expanded')) {
        btn.innerHTML = 'Collapse <i class="fa-solid fa-chevron-up"></i>';
    } else {
        btn.innerHTML = 'Read More <i class="fa-solid fa-chevron-down"></i>';
    }
}