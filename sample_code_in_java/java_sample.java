import java.util.*;
import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

import javax.net.ssl.HttpsURLConnection;

public class HttpURLConnectionExample {

	public static void main(String[] args) throws Exception {
		HttpURLConnectionExample http = new HttpURLConnectionExample();
		http.sendGet();
	}

	// HTTP GET request
	private void sendGet() throws Exception {
		String url = "https://qa2.cradlepointecm.com/api/v2/accounts/";
		URL obj = new URL(url);
		HttpURLConnection con = (HttpURLConnection) obj.openConnection();

		// optional default is GET
		con.setRequestMethod("GET");

		//add request header
		HttpURLConnectionExample http = new HttpURLConnectionExample();
		http.set_headers(con);
		int responseCode = con.getResponseCode();

		System.out.println("\nSending 'GET' request to URL : " + url);
		System.out.println("Response Code : " + responseCode);

                Scanner s = new Scanner(con.getInputStream());
                System.out.println("Response : " + s.useDelimiter("\0").next());

	}

        public HttpURLConnection set_headers(HttpURLConnection con)
	{
                con.setRequestProperty("x-ecm-api-id", "...");
                con.setRequestProperty("x-ecm-api-key", "...");
                con.setRequestProperty("x-cp-api-id", "...");
                con.setRequestProperty("x-cp-api-key", "...");
                con.setRequestProperty("Accept", "*/*");
                return con;
	}
}
