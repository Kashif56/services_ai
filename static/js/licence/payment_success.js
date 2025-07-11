/**
 * Payment Success Page JavaScript
 * 
 * This file contains JavaScript functionality for the payment success page.
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Payment success page loaded');
    
    // Add confetti effect for successful payment
    const confettiDuration = 3000; // 3 seconds
    
    function createConfetti() {
        const colors = ['#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3', '#03a9f4', '#00bcd4', '#009688', '#4CAF50'];
        const confettiCount = 150;
        const container = document.querySelector('.container');
        
        for (let i = 0; i < confettiCount; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            
            // Random position, color, and animation delay
            const color = colors[Math.floor(Math.random() * colors.length)];
            const left = Math.random() * 100;
            const width = Math.random() * 10 + 5;
            const height = width * 0.4;
            const animationDelay = Math.random() * 3;
            
            confetti.style.backgroundColor = color;
            confetti.style.left = left + '%';
            confetti.style.width = width + 'px';
            confetti.style.height = height + 'px';
            confetti.style.animationDelay = animationDelay + 's';
            
            container.appendChild(confetti);
            
            // Remove confetti after animation
            setTimeout(() => {
                confetti.remove();
            }, confettiDuration);
        }
    }
    
    // Start confetti animation
    createConfetti();
});
