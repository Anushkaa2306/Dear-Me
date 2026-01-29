 document.addEventListener('mousemove', (e) => {
            const x = (e.clientX / window.innerWidth) * 10 - 5;
            const y = (e.clientY / window.innerHeight) * 10 - 5;
            document.body.style.backgroundPosition = `${50 + x}% ${50 + y}%`;
        });