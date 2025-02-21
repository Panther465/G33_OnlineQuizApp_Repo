$(document).ready(function() {
    // executes when HTML-Document is loaded and DOM is ready
   
   // breakpoint and up  
   $(window).resize(function(){
       if ($(window).width() >= 980){	
   
         // when you hover a toggle show its dropdown menu
         $(".navbar .dropdown-toggle").hover(function () {
            $(this).parent().toggleClass("show");
            $(this).parent().find(".dropdown-menu").toggleClass("show"); 
          });
   
           // hide the menu when the mouse leaves the dropdown
         $( ".navbar .dropdown-menu" ).mouseleave(function() {
           $(this).removeClass("show");  
         });
     
           // do something here
       }	
   });  
     
     
   
   // document ready  
   });




   document.getElementById('other-btn').addEventListener('click', function() {
    const otherInput = document.getElementById('other-input');
    otherInput.classList.toggle('hidden');
  });
  
  document.getElementById('preference-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const educationLevel = document.getElementById('education-level').value;
    const selectedCategory = document.querySelector('.category-btn.active')?.dataset.category || document.getElementById('custom-category').value;
  
    console.log('Username:', username);
    console.log('Education Level:', educationLevel);
    console.log('Selected Category:', selectedCategory);
  
    // You can add further logic here, like sending data to a server
  });





  /*.............................................................*/
var countDownDate = new Date("Feb 17, 2025 00:00:00").getTime();
var x = setInterval(function(){
      var now = new Date().getTime();
      var distance = countDownDate - now;


      var days = Math.floor(distance / (1000 * 60 * 60 * 24));
      var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      var seconds = Math.floor((distance % (1000 * 60)) / 1000);

      document.getElementById("days").innerHTML = days;
      document.getElementById("hours").innerHTML = hours;
      document.getElementById("minutes").innerHTML = minutes;
      document.getElementById("seconds").innerHTML = seconds;
}, 1000);

// Smooth Scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
      e.preventDefault();
      document.querySelector(this.getAttribute('href')).scrollIntoView({
          behavior: 'smooth'
      });
  });
});

// Newsletter Animation
const newsletterCard = document.querySelector('.newsletter-card');
newsletterCard.addEventListener('mouseenter', () => {
  newsletterCard.style.animation = 'none';
});
newsletterCard.addEventListener('mouseleave', () => {
  newsletterCard.style.animation = 'pulse 2s infinite';
});