var swiper = new Swiper(".verticalSwiper", {
  direction: "vertical",
  pagination: {
    el: ".swiper-pagination",
    clickable: true,
  },
  speed: 1000,
  // speed: 10,
  mousewheel: {
    sensitivity: 1,
  },
  // autoplay: {
  //   delay: 4000,
  //   disableOnInteraction: true,
  // },
 navigation: {
    nextEl: '.swiper-button-next',
    prevEl: '.swiper-button-prev',
  },
});
document.addEventListener("DOMContentLoaded", () => {
  // alert("DOM готов!");

  // function startTimer() {
  //   let count = 3;
  //   setInterval(function() {
  //     let timer = document.querySelector('.timer').textContent = count;
  //     count--;
  //     if (count < 0) {
  //       count = 3; // Сбросить счетчик
  //     }
  //   }, 1000); // Обновлять каждую секунду
  // }
  
  // Запустить таймер при загрузке страницы
  startTimer();


  // let slideTime = 4000;
  // let autoSlideTimeout;
  // if(window.innerWidth >= 1024) {
  //   function AutoListSlide(){
  //     autoSlideTimeout = setTimeout(function(){
  //       swiper.slideTo(1, 1000, true);
  //       autoSlideTimeout = setTimeout(function(){
  //         swiper.slideTo(2, 1000, true);
  //         autoSlideTimeout = setTimeout(function(){
  //           swiper.slideTo(3, 1000, true);
  //           autoSlideTimeout = setTimeout(function(){
  //             swiper.slideTo(4, 1000, true);
  //             autoSlideTimeout = setTimeout(function(){
  //               swiper.slideTo(5, 1000, true);
  //               autoSlideTimeout = setTimeout(function(){
  //                 swiper.slideTo(0, 1000, true);
  //                 AutoListSlide();
  //               }, slideTime);
  //             }, slideTime);
  //           }, slideTime);
  //         }, slideTime);
  //       }, slideTime);
  //     }, slideTime);
  //   }
  // }
  
  function stopAutoSlide() {
    console.log("del")
    clearTimeout(autoSlideTimeout);
    let timers = document.querySelectorAll('.timers')[0];
    timers.classList.add('hidden');
  }
  
  // Добавьте эти обработчики событий в соответствующие элементы
  swiper.on('touchStart', stopAutoSlide);
  window.addEventListener('scroll', stopAutoSlide);
  function onScroll() {
    stopAutoSlide();
  }
  
  // Добавляем обработчик события прокрутки к окну
  window.addEventListener('scroll', onScroll);
  AutoListSlide();
});

// setTimeout(() => {
  
  
// }, 1000);


function toggleAutoplay() {
  // console.log("dasda");
  let slider = document.querySelector('.autoplay');
  slider.classList.toggle('play');

  swiper.autoplay.start();

}
// function toggleAutoplay() {
//   swiper.autoplay.stop();
// }

// Инициализация Swiper
function findContact() {
  swiper.slideTo(5, 1000, true);
  clearTimeout(autoSlideTimeout);
}

function upVector() {
  swiper.slideTo(0, 1000, true);
  clearTimeout(autoSlideTimeout);
}

function openFormPopup() {
  const popup = document.querySelector('.popup');
  let element_fixed = document.querySelector('.element-fixed')
  popup.classList.toggle('__active');
  element_fixed.classList.toggle('__active');
}

