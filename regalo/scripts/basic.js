$(document).ready(function() {
	//Get the path from url
	var  parser = document.createElement('a');
	parser.href = window.location.href;
	var tab = parser.pathname;

	if (tab == '/signin') {
		$('#login_top_cont').remove();
	}

	//toggles edit icon on myposts page
	$("#show_edit_but").click(function(){
    	$(".edit_button").toggle();
	});

	/*$("#prof_edit_but").click(function(){
    	$("#prof_submit_but").toggle();
    	if ($('#prof_submit_but').css("display") == 'block') {
	    	$("#usernametext").attr("contenteditable","true");
	    	$("#useremailtext").attr("contenteditable","true");
	    	$("#usernametext").css("border","1px solid black");
	    	$("#useremailtext").css("border","1px solid black");
	    }
	    else {
	    	$("#usernametext").attr("contenteditable","false");
	    	$("#useremailtext").attr("contenteditable","false");
	    	$("#usernametext").css("border","none");
	    	$("#useremailtext").css("border","none");
	    }
	});*/


	//expands and collapses swap and sell posts on myprofile page
	$("#prof_swap_expand").click(function () {
	    $('#prof_swap_cont').slideToggle(200, function () {
	        $('#prof_sell_cont').hide(200, function () {
	        	;
	    	});
	    	$('#prof_swapbids_cont').hide(200, function () {
	        	;
	    	});
	    });
	});
	$("#prof_sell_expand").click(function () {
	    $('#prof_sell_cont').slideToggle(200, function () {
	        $('#prof_swap_cont').hide(200, function () {
	        	;
	    	});
	    	$('#prof_swapbids_cont').hide(200, function () {
	        	;
	    	});
	    });
	});

	$("#prof_bidswap_expand").click(function () {
	    $('#prof_swapbids_cont').slideToggle(200, function () {
	        $('#prof_sell_cont').hide(200, function () {
	        	;
	    	});
	    	$('#prof_swap_cont').hide(200, function () {
	        	;
	    	});
	    });
	});

	//moves the line under the tabs on the main navigation bar
	 if (tab == '/browse')  {
	  $('#nav_Bar_bottom_line').css("left","0%");
	 }
	 if (tab == '/myprofile' || tab == '/myprofile/edit')  {
	  $('#nav_Bar_bottom_line').css("left","16.3%");
	 }
	 if (tab == '/myposts' || tab == "/myposts/newpost" || tab == '/myposts/editswap') {
	  $('#nav_Bar_bottom_line').css("left","33.4%");
	 }
	 if (tab == '/mybids')  {
	  $('#nav_Bar_bottom_line').css("left","49.8%");
	 }
	 if (tab == '/about')  {
	  $('#nav_Bar_bottom_line').css("left","66.4%");
	 }
	 if (tab == '/help')  {
	  $('#nav_Bar_bottom_line').css("left","84%");
	 }


	 //is used to change the position of green arrow on the side menu
	if (tab == '/browse' || tab == '/myposts') {
		var type = getUrlParameter('type');
		if (type == 1 || type == undefined ) {
			$('#swap_arrow').css("visibility", "visible" );
			$('#sell_arrow').css("visibility", "hidden" );
		}
		if (type == 2 ) {
			$('#swap_arrow').css("visibility", "hidden" );
			$('#sell_arrow').css("visibility", "visible" );
		}
		if (type == 0 ) {
			$('#swap_arrow').css("visibility", "hidden" );
			$('#sell_arrow').css("visibility", "hidden" );
		}	
	}

	//used to extract a get argument from the url
	function getUrlParameter(sParam) {
	    var sPageURL = window.location.search.substring(1);
	    var sURLVariables = sPageURL.split('&');
	    for (var i = 0; i < sURLVariables.length; i++) 
	    {
	        var sParameterName = sURLVariables[i].split('=');
	        if (sParameterName[0] == sParam) 
	        {
	            return sParameterName[1];
	        }
	    }
	}
	

	/*$(".buttonpop").click(function(){
	    $('#mybid-popDiv').fadeIn(400);
	    $('#overlay').fadeIn(100);
	    //$('html').css('overflow-y', 'hidden');

	});*/
	$("#close").click(function(){
	    $('#mybid-popDiv').fadeOut(100);
	    $('#overlay').fadeOut(200);
	    //$('html').css('overflow-y', 'visible');
	});
	$("#overlay").click(function(){
	    $('#mybid-popDiv').fadeOut(100);
	    $('#overlay').fadeOut(200);
	    //$('html').css('overflow-y', 'visible');
	});
	//To detect escape button
	document.onkeydown = function(evt) {
		evt = evt || window.event;
		if (evt.keyCode == 27) {
			$('#mybid-popDiv').fadeOut(100);
		    $('#overlay').fadeOut(200);
		    //$('html').css('overflow-y', 'visible');
		}
	};

	$(function() {
	    $('.buttonpop').click(function(e) {
	        $('#mybid-popDiv').load('/popup-swap?id=' + this.id);
	        $('#mybid-popDiv').fadeIn(200);
	    	$('#overlay').fadeIn(100);
	    });
	});

	$(function() {
	    $('#new_comment_but').click(function(e) {
	        $('#comments_cont').load('/usersform');
	    });
	});

	$(function() {
	    $('#new_comment_but').click(function(e) {
	        $('#comments_cont').load('/usersform');
	    });
	});

	$(function() {
	    $('#prof_submit_but').click(function(e) {
			var user_name = $('#usernametext').html();
			var email = $('#useremailtext').html();
	       	//var posting = $.post('editprof');
			$.ajax({
			    url : "/editprof",
			    type: "POST",
			    success: function(data, textStatus, jqXHR)
			    {
			        $('#usernametext').html() = data;
			    }
			});
		  /*// Put the results in a div
		  posting.done(function( data ) {
		    var user = $( data ).find( "#usertext" );
		    var em = $( data ).find( "#usertext" );
		    $("#usernametext").empty().append(user);
		    $("#useremailtext").empty().append(em);
		  });
	    });*/
		});
	});


	jQuery.ajaxSetup({
	  beforeSend: function() {
		 $('#mybid-loading-indicator').show(100);
	  },
	  complete: function(){
		 
	  },
	  success: function() {
	  	$('#mybid-loading-indicator').hide(100);
	  }
	});

	$('.myMenu > li').bind('mouseover', openSubMenu);
		$('.myMenu > li').bind('mouseout', closeSubMenu);
		
		function openSubMenu() {
			$(this).find('ul').css('visibility', 'visible');	
		};
		
		function closeSubMenu() {
			$(this).find('ul').css('visibility', 'hidden');	
		};

});