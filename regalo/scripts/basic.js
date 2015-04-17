$(document).ready(function() {
	var  parser = document.createElement('a');
	parser.href = window.location.href;
	var tab = parser.pathname;
	if (tab != '/myposts') {
		$('.edit_button').remove();
	}

	/*$('.post_cont').hover(function() {
		var my_id = this.id.substring(2);
		$('#e_' + my_id).css("display", "block");
	}, function () {
		var my_id = this.id.substring(2);
		$('#e_' + my_id).css("display", "none");
	}
	);*/

	$("#show_edit_but").click(function(){
    	$(".edit_button").toggle();
	});


	 if (tab == '/browse')  {
	  $('#nav_Bar_bottom_line').css("left","0%");
	 }
	 if (tab == '/myprofile')  {
	  $('#nav_Bar_bottom_line').css("left","16.3%");
	 }
	 if (tab == '/myposts' || tab == "/myposts/newpost") {
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

});