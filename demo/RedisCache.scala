package RedisCache

import scala.concurrent.duration._

import io.gatling.core.Predef._
import io.gatling.http.Predef._
import io.gatling.jdbc.Predef._

class HighAvailability extends Simulation {

	val httpProtocol = http
		.baseUrl("http://localhost:9090")
		.inferHtmlResources()
		.acceptHeader("text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9")
		.acceptEncodingHeader("gzip, deflate")
		.acceptLanguageHeader("en-US,en-GB;q=0.9,en;q=0.8,fr;q=0.7,de;q=0.6,it;q=0.5,la;q=0.4")
		.doNotTrackHeader("1")
		.upgradeInsecureRequestsHeader("1")
		.userAgentHeader("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36")

	object Cached {
		val cached = repeat(10, "i") {
			exec(
				http("Cached ${i}")
					.get("/cached/cached${i}")
			)
		}
	}

	val users_cached = scenario("Cached").exec(Cached.cached)

	setUp(
		users_cached.inject(rampUsers(1000) during (10 seconds))
	).protocols(httpProtocol)

}

class LowAvailability extends Simulation {

	val httpProtocol = http
		.baseUrl("http://localhost:9090")
		.inferHtmlResources()
		.acceptHeader("text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9")
		.acceptEncodingHeader("gzip, deflate")
		.acceptLanguageHeader("en-US,en-GB;q=0.9,en;q=0.8,fr;q=0.7,de;q=0.6,it;q=0.5,la;q=0.4")
		.doNotTrackHeader("1")
		.upgradeInsecureRequestsHeader("1")
		.userAgentHeader("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36")

	object Cached {
		val cached = repeat(10, "i") {
			exec(
				http("Cached ${i}")
					.get("/cached/cached${i}")
			).pause(1)
		}
	}

	val users_cached = scenario("Cached").exec(Cached.cached)

	setUp(
		users_cached.inject(rampUsers(100) during (10 seconds))
	).protocols(httpProtocol)

}

class Direct extends Simulation {

	val httpProtocol = http
		.baseUrl("http://localhost:9090")
		.inferHtmlResources()
		.acceptHeader("text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9")
		.acceptEncodingHeader("gzip, deflate")
		.acceptLanguageHeader("en-US,en-GB;q=0.9,en;q=0.8,fr;q=0.7,de;q=0.6,it;q=0.5,la;q=0.4")
		.doNotTrackHeader("1")
		.upgradeInsecureRequestsHeader("1")
		.userAgentHeader("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36")

	object Direct {
		val direct = repeat(10, "i") {
			exec(
				http("Direct ${i}")
					.get("/direct/direct${i}")
			).pause(1)
		}
	}

	val users_direct = scenario("Direct").exec(Direct.direct)

	setUp(
		users_direct.inject(rampUsers(100) during (10 seconds))
	).protocols(httpProtocol)

}